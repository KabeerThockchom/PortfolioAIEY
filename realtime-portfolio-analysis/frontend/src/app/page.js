

"use client";
import React, {
  useEffect,
  useState,
  useCallback,
  useRef,
  Fragment,
} from "react";
import Header from "./component/header/header";
import ChatLayout from "./component/chatLayout";
import SidebarContent from "./component/layout/sideBarContent";
import protobuf from "protobufjs";
import Login from "./component/login";

const SAMPLE_RATE = 16000;
const NUM_CHANNELS = 1;

export default function Home() {
  const [chartConfig, setChartConfig] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false); // NEW
  const [isMuted, setIsMuted] = useState(false);
  const [Frame, setFrame] = useState(null);
  const [audioContext, setAudioContext] = useState(null);
  const [ws, setWs] = useState(null);
  const [sessionLogs, setSessionLogs] = useState([]);
  const [userSession, setUserSession] = useState(null);

  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const [isRealtime, setIsRealtime] = useState(true);

  const isMutedRef = useRef(false);

  const [newsData, setNewsData] = useState(null);
  const [fundFactSheetData, setFundFactSheetData] = useState(null);
  const [tradeData, setTradeData] = useState(null);
  const [ragData, setRagData] = useState(null);
  const [ragResponse, setRagResponse] = useState(null);

  // NEW: Cash balance state and fetcher
  const [cashBalance, setCashBalance] = useState(0);
  const [loadingCash, setLoadingCash] = useState(false);

  const fetchCashBalance = useCallback(async () => {
    let userId = null;
    try {
      const userStr = localStorage.getItem('user');
      if (userStr) {
        const userObj = JSON.parse(userStr);
        userId = userObj.data.user_id;
      }
    } catch (e) {
      userId = null;
    }

    if (!userId) {
      setCashBalance(0);
      return;
    }
    setLoadingCash(true);
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/cash_balance?user_id=${userId}`,
        // `https://rtpa-be.azurewebsites.net/api/cash_balance?user_id=${userId}`,

        {
          method: "GET",
          headers: { Accept: "application/json" },
        }
      );
      if (!response.ok) {
        setCashBalance(0);
        setLoadingCash(false);
        return;
      }
      const data = await response.json();
      setCashBalance(Number(data.cash_balance));
    } catch (error) {
      setCashBalance(0);
    } finally {
      setLoadingCash(false);
    }
  }, []);

  useEffect(() => {
    isMutedRef.current = isMuted;
  }, [isMuted]);

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    if (storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        setUserSession(parsedUser);
        setIsLoggedIn(true);
        fetchCashBalance(); // Fetch on login/mount
      } catch (error) {
        console.error("Error parsing user from localStorage:", error);
      }
    }
    protobuf.load("/assets/frames.proto", (err, root) => {
      if (err) {
        console.error("Error loading protobuf:", err);
        return;
      }
      if (root) {
        setFrame(root.lookupType("pipecat.Frame"));
      }
    });
  }, [fetchCashBalance]);

  useEffect(() => {
    if (ws && isRecording) {
      setIsConnecting(true);
      setIsRecording(false);
      stopAudio(true);
      setTimeout(() => {
        startAudio();
      }, 200);
    }
  }, [isRealtime]);

  const startAudio = async () => {
    if (!Frame) {
      alert("Protobuf is not loaded yet.");
      return;
    }
    setIsConnecting(true); // NEW: show connecting state

    const wsUrl = `ws://127.0.0.1:8000/ws?phonenumber=12345678901&voice=ash&log_needed=false&realtime=${isRealtime}`;

    // const wsUrl = `wss://rtpa-be.azurewebsites.net/ws?phonenumber=12345678901&voice=ash&log_needed=false&realtime=${isRealtime}`;

    const newAudioContext = new (window.AudioContext ||
      window.webkitAudioContext)({
      latencyHint: "interactive",
      sampleRate: SAMPLE_RATE,
    });
    setAudioContext(newAudioContext);

    const newWs = new WebSocket(wsUrl);
      // `wss://rtpa-be.azurewebsites.net/ws?phonenumber=12345678901&voice=ash&log_needed=false&realtime=true`
    newWs.binaryType = "arraybuffer";

    newWs.addEventListener("open", () => {
            console.log("WebSocket connection established.");
      setIsRecording(true);    // Only set to true after connection is open
      setIsConnecting(false);  // Done connecting
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
          const source = newAudioContext.createMediaStreamSource(stream);
          const scriptProcessor = newAudioContext.createScriptProcessor(
            512,
            1,
            1
          );

          source.connect(scriptProcessor);
          scriptProcessor.connect(newAudioContext.destination);

          scriptProcessor.onaudioprocess = (event) => {
            // Use ref to get current mute state instead of closure
            if (!newWs || isMutedRef.current) return;

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
            newWs.send(encodedFrame);
          };
        })
        .catch((error) => console.error("Error accessing microphone:", error));
    });

    newWs.addEventListener("message", (event) => {
      if (event.data instanceof ArrayBuffer) {
        const arrayBuffer = event.data;
        enqueueAudioFromProto(arrayBuffer, newAudioContext);
      } else {
        const dataType = JSON.parse(event.data);
        if (
          dataType.query_type === "trade_response" ||
          dataType.query_type === "user_portfolio"
        ) {
          fetchCashBalance();
        }
        if (
          dataType.query_type === "aggregation_level_2" ||
          dataType.query_type === "aggregation_level_1" ||
          dataType.query_type === "user_portfolio" ||
          dataType.query_type === "relative_performance" ||
          dataType.query_type === "portfolio_benchmark" ||
          dataType.query_type === "risk_analysis" ||
          dataType.query_type === "returns_attribution"
        ) {
          console.log("Chart config received:", dataType);
          setChartConfig(dataType);
        } else if (dataType.query_type === "session_logs") {
          console.log("Session logs received:", dataType);
          setSessionLogs((prevLogs) => [
            ...prevLogs,
            {
              type: dataType.data.type,
              datetime: dataType.data.datetime,
              message: dataType.data.message,
            },
          ]);
        } else if (dataType.query_type === "news") {
          setNewsData(dataType);
        } else if (dataType.query_type === "fund_fact_sheet") {
          setFundFactSheetData(dataType);
        } else if (dataType.query_type === "trade_response") {
          setTradeData(dataType);
        } else if (dataType.type === "rag_context") {
          setRagData(dataType);
        }
         else if (dataType.query_type === "rag_response") {
          setRagResponse(dataType);
        }
      }
    });
    newWs.addEventListener("close", () => {
      setIsRecording(false);
      setIsConnecting(false);
        console.log("WebSocket connection closed.");
      stopAudio(false);
    });

    newWs.addEventListener("error", (event) => {
      setIsRecording(false);
      setIsConnecting(false);
      console.error("WebSocket error:", event);
    });

    setWs(newWs);
    setIsMuted(false);
  };

  const stopAudio = (closeWebSocket) => {
    setIsRecording(false);
    setIsConnecting(false);
    setIsMuted(false);
    if (ws && closeWebSocket) {
      ws.close();
      setWs(null);
    }
    if (audioContext) {
      audioContext.close();
      setAudioContext(null);
    }
  };

  let playTime = 0;

  const enqueueAudioFromProto = (arrayBuffer, context) => {
    if (isMutedRef.current) return;
    const parsedFrame = Frame.decode(new Uint8Array(arrayBuffer));
    if (!parsedFrame?.audio) return;

    const audioVector = Array.from(parsedFrame.audio.audio);
    const audioArray = new Uint8Array(audioVector);
    context.decodeAudioData(audioArray.buffer, (buffer) => {
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(context.destination);

      if (playTime < context.currentTime) {
        playTime = context.currentTime;
      }
      source.start(playTime);
      playTime += buffer.duration;
    });
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
    if (!isRecording && !isConnecting) {
      await startAudio();
    } else if (isRecording && !isConnecting) {
      stopAudio(true);
    }
  };

  const toggleMute = () => {
    if (isRecording && !isConnecting) {
      setIsMuted(!isMuted);
    }
  };

  const onLogin = useCallback(async (sessionData) => {
    if (sessionData && sessionData.data.user_id) {
      setUserSession(sessionData);
      setIsLoggedIn(true);
      fetchCashBalance();
    }
  }, [fetchCashBalance]);

  const onLogout = useCallback(() => {
    setIsLoggedIn(false);
    setUserSession(null);
    setSessionLogs([]);
    stopAudio(true);
    localStorage.removeItem("user");
    // if (ws) {
    //   ws.close();
    //   setWs(null);
    // }
    // if (audioContext) {
    //   audioContext.close();
    //   setAudioContext(null);
    // }
  }, []);

  const changePipeline = useCallback((pipeline) => {
    console.log("Changing pipeline to:", pipeline);
    setIsRecording(true);
    stopAudio(true);
    // startAudio();
  }, []);

  const micTemplate = useCallback(() => {
    return (
      <div className="flex items-center gap-3">
        <button
          className={`rounded-full p-3 border-2 transition-all duration-200 ${
            isRecording
              ? "border-green-400 bg-gradient-to-tr from-green-400/30 to-green-500/10"
              : isConnecting
              ? "border-yellow-400 bg-gradient-to-tr from-yellow-400/30 to-yellow-500/10 animate-pulse"
              : "border-slate-600 bg-slate-800 hover:bg-slate-700"
          }`}
          onClick={onToggleListening}
          aria-label={isRecording ? "Disconnect" : "Connect"}
          disabled={isConnecting}
        >
          {isConnecting ? (
            // Spinner icon
            <svg className="animate-spin w-7 h-7 text-yellow-400" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            </svg>
          ) : isRecording ? (
            // Connected - Power on icon
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              className="w-7 h-7 text-green-400"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          ) : (
            // Disconnected - Power off icon
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              className="w-7 h-7 text-slate-400"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4"
              />
            </svg>
          )}
        </button>

        {/* Mic Mute/Unmute button */}
        {isRecording && (
          <button
            className={`rounded-full p-3 border-2 transition-all duration-200 ${
              !isMuted
                ? "border-blue-400 bg-gradient-to-tr from-blue-400/30 to-blue-500/10 animate-pulse"
                : "border-red-400 bg-gradient-to-tr from-red-400/30 to-red-500/10"
            }`}
            onClick={toggleMute}
            aria-label={isMuted ? "Unmute microphone" : "Mute microphone"}
            disabled={isConnecting}
          >
            {!isMuted ? (
              // Unmuted microphone
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="currentColor"
                className="w-4 h-4 text-blue-400"
                viewBox="0 0 24 24"
              >
                <path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3zm5-3a1 1 0 1 1 2 0 7 7 0 0 1-6 6.93V21a1 1 0 1 1-2 0v-2.07A7 7 0 0 1 5 12a1 1 0 1 1 2 0 5 5 0 0 0 10 0z" />
              </svg>
            ) : (
              // Muted microphone
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="currentColor"
                className="w-4 h-4 text-red-400"
                viewBox="0 0 24 24"
              >
                <path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3zm5-3a1 1 0 1 1 2 0 7 7 0 0 1-6 6.93V21a1 1 0 1 1-2 0v-2.07A7 7 0 0 1 5 12a1 1 0 1 1 2 0 5 5 0 0 0 10 0z" />
                <path
                  d="M3 3l18 18"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
              </svg>
            )}
          </button>
        )}

        {/* Enhanced status indicator */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                isRecording
                  ? "bg-green-400 animate-pulse"
                  : isConnecting
                  ? "bg-yellow-400 animate-pulse"
                  : "bg-red-400"
              }`}
            ></div>
            <span className="text-xs text-slate-400 font-medium">
              {isConnecting
                ? "Connecting..."
                : isRecording
                ? "Connected"
                : "Disconnected"}
            </span>
          </div>
          {isRecording && (
            <div className="flex items-center gap-2">
              <div
                className={`w-1.5 h-1.5 rounded-full ${
                  !isMuted
                    ? "bg-blue-400 animate-pulse"
                    : "bg-red-400"
                }`}
              ></div>
              <span className="text-xs text-slate-500">
                {isMuted ? "Muted" : "Live"}
              </span>
            </div>
          )}
        </div>
      </div>
    );
  }, [isRecording, isMuted, isConnecting, onToggleListening, toggleMute]);

  const showSessionLogs = () => {
    const LOG_COLORS = {
      INFO: "text-green-400",
      ERROR: "text-red-400",
      WARNING: "text-yellow-400",
    };

    // Define colors for specific message prefixes  
    const MESSAGE_COLORS = {
      USER: "text-orange-300", // Orange for "User Said"  
      BOT: "text-blue-300", // Blue for "Bot Said"  
      ERROR: "text-red-400", // Red for "Error" messages
      DISCONNECT: "text-yellow-400",
      DEFAULT: "text-white",  // Default white color for other messages  
    };

    return (
      <div className="w-full max-w-full space-y-1 text-xs">
        {sessionLogs.map((log, index) => {
        // Determine the text color for the message based on its prefix  
          const messageColor = log.message.startsWith("User Said")
            ? MESSAGE_COLORS.USER
            : log.message.startsWith("Bot Said")
            ? MESSAGE_COLORS.BOT
            : log.message.includes("fatal error")
            ? MESSAGE_COLORS.ERROR
            : log.message.includes("Client disconnected")
            ? MESSAGE_COLORS.DISCONNECT
            : MESSAGE_COLORS.DEFAULT;

          return (
            <div
              key={index}
              className="flex flex-wrap w-full break-words items-baseline"
            >
              <span
                className={`${
                  LOG_COLORS[log.type] || "text-gray-400"
                } font-semibold mr-2`}
              >
                {log.type}
              </span>
              <span className="text-gray-500 mr-2">{log.datetime}</span>
            <span  
              // className={`${messageColor} bg-gray-800 px-1 py-0.5 rounded`}
              className={`${messageColor}`}  
            >  
              {log.message}  
            </span>  
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="min-h-screen  bg-gray-800	bg-gray-700 border-gray-600	bg-gray-700 border-b border-gray-600	bg-gray-600 border border-gray-500">
      {isLoggedIn && (
        <Fragment>
          <Header
            micTemplate={micTemplate}
            portfolioData={chartConfig}
            onLogout={onLogout}
            changePipeline={changePipeline}
            userSession={userSession}
            isRealtime={isRealtime}
            setIsRealtime={setIsRealtime}
            cashBalance={cashBalance}
            loadingCash={loadingCash}
          />
          <div className="flex">
            <aside className="fixed top-16 left-0 h-[calc(100vh-4rem)] w-72 bg-gray-800 bg-gray-700 border-gray-600 bg-gray-700 border-b border-gray-600 bg-gray-600 border border-gray-500 shadow-lg z-20">
              <SidebarContent showSessionLogs={showSessionLogs} />
            </aside>
            <main className="ml-72 mt-16 flex-1 min-h-screen p-6 flex flex-col">
              <div className="flex-1 min-h-0 flex flex-col bg-slate-900/80 shadow-xl rounded-2xl p-6">
                <ChatLayout
                  chartConfig={chartConfig}
                  newsData={newsData}
                  fundFactSheetData={fundFactSheetData}
                  tradeData={tradeData}
                  ragData={ragData}
                  ragResponse={ragResponse}
                />
              </div>
            </main>
          </div>
        </Fragment>
      )}
      {!isLoggedIn && <Login onLogin={onLogin} />}
    </div>
  );
}
