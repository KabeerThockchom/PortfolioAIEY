import json
from src.pipeline.logger import logger
from pipecat.frames.frames import (
    LLMFullResponseEndFrame, 
    LLMTextFrame, 
)
from pipecat.utils.time import time_now_iso8601
from pipecat.metrics.metrics import LLMTokenUsage
from pipecat.services.openai.base_llm import BaseOpenAILLMService
from openai.types.chat import ChatCompletionChunk
from openai import AsyncStream
from pipecat.processors.aggregators.openai_llm_context import (
    OpenAILLMContext,
)
from pipecat.frames.frames import (
    TranscriptionFrame, 
    LLMFullResponseEndFrame, 
    ErrorFrame, 
    LLMTextFrame,
    EndFrame,
    CancelFrame,
    StopFrame,
    EndTaskFrame,
    CancelTaskFrame,
    StopTaskFrame, 
)
from pipecat.utils.time import time_now_iso8601
from pipecat.metrics.metrics import LLMTokenUsage
from pipecat.services.openai.base_llm import BaseOpenAILLMService
from openai.types.chat import ChatCompletionChunk
from openai import AsyncStream
from pipecat.services.openai_realtime_beta import (
    OpenAIRealtimeBetaLLMService,
)
from pipecat.pipeline.task import PipelineTask
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam
import base64
from typing import List

################################# For realtime patching ##################################

# Save the original method  
original_handle_evt_input_audio_transcription_completed = OpenAIRealtimeBetaLLMService.handle_evt_input_audio_transcription_completed 

# Create a patched version of the method  
async def patched_handle_evt_input_audio_transcription_completed(self, evt):  
    await self._call_event_handler("on_conversation_item_updated", evt.item_id, None)  
  
    if self._send_transcription_frames:  
        await self.push_frame(  
            TranscriptionFrame(evt.transcript, "", time_now_iso8601())  
        )  
  
    pair = self._user_and_response_message_tuple  
    if pair:  
        user, assistant = pair  
        user.content[0].transcript = evt.transcript  
  
        # Add the log entry for the user transcript  
        logger.bind(frontend=True).info(f"User Said: {user.content[0].transcript}")   
  
        if assistant["done"]:  
            self._user_and_response_message_tuple = None  
            self._context.add_user_content_item_as_message(user)  
            await self._handle_assistant_output(assistant["output"])  
    else:  
        logger.warning(f"Transcript for unknown user message: {evt}")  
  
# Apply the patch  
OpenAIRealtimeBetaLLMService.handle_evt_input_audio_transcription_completed = patched_handle_evt_input_audio_transcription_completed  

########## Realtime BOT Message patching #########
original_handle_evt_response_done = OpenAIRealtimeBetaLLMService._handle_evt_response_done

async def patched_handle_evt_response_done(self, evt):
        # todo: figure out whether there's anything we need to do for "cancelled" events
        # usage metrics
        tokens = LLMTokenUsage(
            prompt_tokens=evt.response.usage.input_tokens,
            completion_tokens=evt.response.usage.output_tokens,
            total_tokens=evt.response.usage.total_tokens,
        )
        await self.start_llm_usage_metrics(tokens)
        await self.stop_processing_metrics()
        await self.push_frame(LLMFullResponseEndFrame())
        self._current_assistant_response = None
        # error handling
        if evt.response.status == "failed":
            await self.push_error(
                ErrorFrame(error=evt.response.status_details["error"]["message"], fatal=True)
            )
            return
        # response content
        for item in evt.response.output:
            if item.content and item.content[0].transcript:
                logger.bind(frontend=True).info(f"Bot Said: {item.content[0].transcript}")
            await self._call_event_handler("on_conversation_item_updated", item.id, item)
        pair = self._user_and_response_message_tuple
        if pair:
            user, assistant = pair
            assistant["done"] = True
            assistant["output"] = evt.response.output
            if user.content[0].transcript is not None:
                self._user_and_response_message_tuple = None
                self._context.add_user_content_item_as_message(user)
                await self._handle_assistant_output(assistant["output"])
        else:
            # Response message without preceding user message. Add it to the context.
            await self._handle_assistant_output(evt.response.output)

# Apply the patch  
OpenAIRealtimeBetaLLMService._handle_evt_response_done = patched_handle_evt_response_done


####################### For Pipeline patching #############################

###### Patching the BOT message logging for OpenAI LLM Service ######
# This patch is to ensure that the bot message is logged correctly in the OpenAI LLM
original_process_context = BaseOpenAILLMService._process_context
class OpenAIUnhandledFunctionException(Exception):
    pass

async def patched_process_context(self, context: OpenAILLMContext):

    functions_list = []  
    arguments_list = []  
    tool_id_list = []  
    func_idx = 0  
    function_name = ""  
    arguments = ""  
    tool_call_id = "" 
  
    # To accumulate the full bot message  
    full_bot_message = []  
  
    await self.start_ttfb_metrics()  
    chunk_stream: AsyncStream[ChatCompletionChunk] = await self._stream_chat_completions(context)  
  
    async for chunk in chunk_stream:  
        if chunk.usage:  
            tokens = LLMTokenUsage(  
                prompt_tokens=chunk.usage.prompt_tokens,  
                completion_tokens=chunk.usage.completion_tokens,  
                total_tokens=chunk.usage.total_tokens,  
            )  
            await self.start_llm_usage_metrics(tokens)  
  
        if chunk.choices is None or len(chunk.choices) == 0:  
            continue  
  
        await self.stop_ttfb_metrics()  
  
        if not chunk.choices[0].delta:  
            continue  
  
        if chunk.choices[0].delta.tool_calls:  
            tool_call = chunk.choices[0].delta.tool_calls[0]  
            if tool_call.index != func_idx:  
                functions_list.append(function_name)  
                arguments_list.append(arguments)  
                tool_id_list.append(tool_call_id)  
                function_name = ""  
                arguments = ""  
                tool_call_id = ""  
                func_idx += 1  
            if tool_call.function and tool_call.function.name:  
                function_name += tool_call.function.name  
                tool_call_id = tool_call.id  
            if tool_call.function and tool_call.function.arguments:  
                arguments += tool_call.function.arguments  
  
        elif chunk.choices[0].delta.content:  
            # Append the bot message chunk to the accumulator  
            full_bot_message.append(chunk.choices[0].delta.content)  
  
            # Push the chunked frame (if necessary for streaming)  
            await self.push_frame(LLMTextFrame(chunk.choices[0].delta.content))  
  
    # Log the full bot message after all chunks are processed  
    if full_bot_message:  
        full_message = "".join(full_bot_message)  
        logger.bind(frontend=True).info(f"Bot Said: {full_message}")  

    # Process function calls only once  
    if function_name and arguments:  
        functions_list.append(function_name)  
        arguments_list.append(arguments)  
        tool_id_list.append(tool_call_id)  
  
        for index, (function_name, arguments, tool_id) in enumerate(  
            zip(functions_list, arguments_list, tool_id_list), start=1  
        ):  
            if self.has_function(function_name):  
                run_llm = False  
                arguments = json.loads(arguments)  
                await self.call_function(  
                    context=context,  
                    function_name=function_name,  
                    arguments=arguments,  
                    tool_call_id=tool_id,  
                    run_llm=run_llm,  
                )  
            else:  
                raise OpenAIUnhandledFunctionException(  
                    f"The LLM tried to call a function named '{function_name}', but there isn't a callback registered for that function."  
                )  
  
# Apply the patch
BaseOpenAILLMService._process_context = patched_process_context


################# Patching the User Message for STT - TTS #################
# This patch is to ensure that the user message is logged correctly for STT - TTS
orginal_stream_chat_completions = BaseOpenAILLMService._stream_chat_completions

async def patched_stream_chat_completions(
        self, context: OpenAILLMContext
    ) -> AsyncStream[ChatCompletionChunk]:  
    logger.debug(f"{self}: Generating chat [{context.get_messages_for_logging()}]")  

    messages: List[ChatCompletionMessageParam] = context.get_messages()  

    # Parse JSON string if necessary  
    if isinstance(messages, str):  
        try:  
            messages = json.loads(messages)  
        except json.JSONDecodeError as e:  
            print("Error decoding JSON:", e)  
            messages = []  # Fallback to an empty list  

    if not hasattr(self, "_last_logged_user_message"):  
        setattr(self, "_last_logged_user_message", None)  # Initialize it to None

    last_user_message = next(  
        (message['content'] for message in reversed(messages) if message['role'] == 'user'),  
        None  
    )

    # Check if the message is the same as the last logged one  
    if last_user_message != self._last_logged_user_message and last_user_message is not None:  
        # Log the message and update the last logged message  
        logger.bind(frontend=True).info(f"User Said: {last_user_message}")  
        self._last_logged_user_message = last_user_message  

    # Base64 encode any images  
    for message in messages:  
        if message.get("mime_type") == "image/jpeg":  
            encoded_image = base64.b64encode(message["data"].getvalue()).decode("utf-8")  
            text = message["content"]  
            message["content"] = [  
                {"type": "text", "text": text},  
                {  
                    "type": "image_url",  
                    "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"},  
                },  
            ]  
            del message["data"]  
            del message["mime_type"]  

    chunks = await self.get_chat_completions(context, messages)  
    return chunks

# Patch the method
BaseOpenAILLMService._stream_chat_completions = patched_stream_chat_completions



### Fatal Error Frame Patch ###
original_process_up_queue = PipelineTask._process_up_queue
async def patched_process_up_queue(self):
    """This is the task that processes frames coming upstream from the
    pipeline. These frames might indicate, for example, that we want the
    pipeline to be stopped (e.g. EndTaskFrame) in which case we would send
    an EndFrame down the pipeline.

    """
    while True:
        frame = await self._up_queue.get()

        if isinstance(frame, self._reached_upstream_types):
            await self._call_event_handler("on_frame_reached_upstream", frame)

        if isinstance(frame, EndTaskFrame):
            # Tell the task we should end nicely.
            await self.queue_frame(EndFrame())
        elif isinstance(frame, CancelTaskFrame):
            # Tell the task we should end right away.
            await self.queue_frame(CancelFrame())
        elif isinstance(frame, StopTaskFrame):
            # Tell the task we should stop nicely.
            await self.queue_frame(StopFrame())
        elif isinstance(frame, ErrorFrame):
            if frame.fatal:
                logger.error(f"A fatal error occurred: {frame}")
                logger.bind(frontend=True).error(f"A fatal error occurred, please check the logs for more details")
                # Cancel all tasks downstream.
                await self.queue_frame(CancelFrame())
                # Tell the task we should stop.
                await self.queue_frame(StopTaskFrame())
            else:
                logger.warning(f"Something went wrong: {frame}")
        self._up_queue.task_done()

PipelineTask._process_up_queue = patched_process_up_queue        