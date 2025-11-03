"use client";
import React, { useEffect, useState, useRef, Image, Fragment } from "react";
import { IconButton, CircularProgress } from "@mui/material";
import MicIcon from "@mui/icons-material/Mic";
import protobuf from "protobufjs";

const SAMPLE_RATE = 16000;
const NUM_CHANNELS = 1;

const BottomLayout = ({ sendMessage, lastMessage }) => {
  const [greeting, setGreeting] = useState(false);
  useEffect(() => {
    if (lastMessage !== null) {
      if (lastMessage.data instanceof ArrayBuffer) {
        console.log("Received ArrayBuffer:", lastMessage.data);
        enqueueAudioFromProto(lastMessage.data);
        // Process the ArrayBuffer (e.g., decode it)
      } else if (lastMessage.data instanceof Blob) {
        console.warn("Received Blob. Converting to ArrayBuffer...");
        lastMessage.data.arrayBuffer().then((arrayBuffer) => {
          // console.log("Converted Blob to ArrayBuffer:", arrayBuffer);
          enqueueAudioFromProto(arrayBuffer);
          // Process the ArrayBuffer
        });
      } else {
        console.warn("Unexpected data type:", lastMessage.data);
      }
    }
  }, [lastMessage]);

  const [isRecording, setIsRecording] = useState(false);
  // Removed unused progressText state
  const [Frame, setFrame] = useState(null);
  const playbackAudioContextRef = useRef(
    typeof window !== "undefined"
      ? new (window.AudioContext || window.webkitAudioContext)({
          latencyHint: "interactive",
          sampleRate: SAMPLE_RATE,
        })
      : null
  );
  const micAudioContextRef = useRef(null);

  const mediaStreamRef = useRef(null);
  const playTimeRef = useRef(0); // UseRef to track playback time

  useEffect(() => {
    // Load the protobuf file
    protobuf.load("/assets/frames.proto", (err, root) => {
      if (err) {
        console.error("Error loading protobuf:", err);
        return;
      }
      if (root) {
        setFrame(root.lookupType("pipecat.Frame"));
      }
      // Removed unused setProgressText call
    });
  }, []);

  const startAudio = async () => {
    if (!Frame) {
      alert("Protobuf is not loaded yet.");
      return;
    }

    //Reinitialize AudioContext if it is closed
    if (
      !micAudioContextRef.current ||
      micAudioContextRef.current.state === "closed"
    ) {
       console.log("Reinitializing AudioContext...");
      micAudioContextRef.current = new (window.AudioContext ||
        window.webkitAudioContext)({
        latencyHint: "interactive",
        sampleRate: SAMPLE_RATE,
      });
    }

    if (!greeting) {
      sendMessage(JSON.stringify({message: "Send Greeting"}));
      setGreeting(true);
    }

    navigator.mediaDevices
      .getUserMedia({
        audio: {
          sampleRate: SAMPLE_RATE,
          channelCount: NUM_CHANNELS,
          autoGainControl: true,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
      .then((stream) => {
        // Stop the previous MediaStream if it exists
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
        }

        mediaStreamRef.current = stream; // Save the MediaStream
        const source =
          micAudioContextRef.current.createMediaStreamSource(stream);
        const scriptProcessor =
          micAudioContextRef.current.createScriptProcessor(512, 1, 1);

        source.connect(scriptProcessor);
        scriptProcessor.connect(micAudioContextRef.current.destination);

        scriptProcessor.onaudioprocess = (event) => {
          //if (!newWs) return;

          const audioData = event.inputBuffer.getChannelData(0);
          const pcmS16Array = convertFloat32ToS16PCM(audioData);
          const pcmByteArray = new Uint8Array(pcmS16Array.buffer);

          const frame = Frame.create({
            audio: {
              audio: Array.from(pcmByteArray),
              sampleRate: SAMPLE_RATE,
              numChannels: NUM_CHANNELS,
            },
          });

          const encodedFrame = new Uint8Array(Frame.encode(frame).finish());

          sendMessage(encodedFrame);
        };
      })
      .catch((error) => console.log("Error accessing microphone:", error));
    setIsRecording(true);
  };

  const stopAudio = () => {
    // if (mediaStreamRef.current) {
    //   // Stop all tracks of the MediaStream
    //   mediaStreamRef.current.getTracks().forEach((track) => track.stop());
    //   mediaStreamRef.current = null; // Clear the reference
    // }

    if (micAudioContextRef.current && micAudioContextRef.current.state !== "closed") {
      // Close the AudioContext only if it is not already closed
      micAudioContextRef.current
        .close()
        .then(() => {
          console.log("Mic AudioContext closed successfully.");
          micAudioContextRef.current = null; // Clear the AudioContext reference
        })
        .catch((error) => {
          console.error("Error closing Mic AudioContext:", error);
        });
    }
    setIsRecording(false);
  };

  const enqueueAudioFromProto = (arrayBuffer) => {
    if (!playbackAudioContextRef.current) {
      console.error("AudioContext is not initialized.");
      return;
    }

    const parsedFrame = Frame.decode(new Uint8Array(arrayBuffer));
    if (!parsedFrame?.audio) return;

    //const audioVector = Array.from(parsedFrame.audio.audio);
    const audioVector = Array.from(parsedFrame.audio.audio);
    const audioArray = new Uint8Array(audioVector);

    playbackAudioContextRef.current.decodeAudioData(
      audioArray.buffer,
      (buffer) => {
        const source = playbackAudioContextRef.current.createBufferSource();
        source.buffer = buffer;
        source.connect(playbackAudioContextRef.current.destination);

        // Ensure audio frames are played sequentially
        if (playTimeRef.current < playbackAudioContextRef.current.currentTime) {
          playTimeRef.current = playbackAudioContextRef.current.currentTime;
        }
        source.start(playTimeRef.current);
        playTimeRef.current += buffer.duration; // Increment playTime by the duration of the buffer
      }
    );
  };

  const convertFloat32ToS16PCM = (float32Array) => {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const clampedValue = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] =
        clampedValue < 0 ? clampedValue * 32768 : clampedValue * 32767;
    }
    return int16Array;
  };

  const onToggleListening = async () => {
    if (!isRecording) {
      await startAudio();
    } else {
      stopAudio();
    }
  };

  return (
    <div className="flex justify-center h-[10%]">
      <div className="flex">
        <div
          onClick={() => {
            onToggleListening();
          }}
        >
          {!isRecording && (
            <IconButton
              color="primary"
              size="large"
              className={isRecording ? "animate-pulse" : ""}
            >
              <MicIcon
                style={{
                  color: isRecording ? "#ffe600" : "#747480",
                  transform: isRecording ? "scale(1.5)" : "scale(1)",
                  transition: "transform 0.3s ease, color 0.3s ease",
                }}
              />
            </IconButton>
          )}
          {isRecording && (
            <Fragment>
              <img
                src="./recording.gif"
                alt="Recording"
                width={60}
                height={60}
                style={{ position: "absolute", zIndex: 1 }}
              />
              {/* <span>Click to mute</span> */}
            </Fragment>
          )}
        </div>
      </div>
    </div>
  );
};

export default BottomLayout;
