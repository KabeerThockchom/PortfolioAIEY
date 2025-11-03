// import React from "react";

// export default function RAGContextWidget({ ragContext }) {
//   if (!ragContext) return null;

//   // If you want to filter out images without base64 data:
//   const filteredImages = Array.isArray(ragContext.image_context)
//     ? ragContext.image_context.filter(img => img.image_base64)
//     : [];

//   return (
//     <div className="w-full max-w-xs mt-8 bg-gray-700 border border-gray-600 rounded-xl p-4 shadow">
//       <h3 className="text-base font-semibold text-slate-100 mb-2">
//         Context for Query:{" "}
//         <span className="font-normal italic text-slate-300">
//           "{ragContext.query || "—"}"
//         </span>
//       </h3>

//       {/* Text Context */}
//       {Array.isArray(ragContext.text_context) && ragContext.text_context.length > 0 && (
//         <div className="mb-4">
//           <h4 className="text-xs font-semibold text-slate-400 mb-1">Text Sources:</h4>
//           <ul className="list-disc list-inside space-y-1 text-xs text-slate-200">
//             {ragContext.text_context.map((text, idx) => (
//               <li key={`text-${idx}`}>{text}</li>
//             ))}
//           </ul>
//         </div>
//       )}

//       {/* Image Context */}
//       {/* {filteredImages.length > 0 && (
//         <div>
//           <h4 className="text-xs font-semibold text-slate-400 mb-1">Image Sources:</h4>
//           <div className="grid grid-cols-1 gap-3">
//             {filteredImages.map((imgCtx, idx) => (
//               <div key={`img-${idx}`} className="flex flex-col items-center bg-gray-800 rounded-lg p-2">
//                 {imgCtx.image_base64 ? (
//                   <img
//                     src={imgCtx.image_base64}
//                     alt={imgCtx.caption || `Context Image ${idx + 1}`}
//                     className="w-24 h-24 object-contain rounded mb-1 border border-gray-600"
//                   />
//                 ) : (
//                   <div className="text-xs text-red-400">Image unavailable</div>
//                 )}
//                 <div className="text-xs text-slate-300 text-center">{imgCtx.caption || "No caption"}</div>
//                 <div className="text-xs text-slate-500 text-center">{imgCtx.file_name || "Unknown file"}</div>
//               </div>
//             ))}
//           </div>
//         </div>
//       )} */}
//    {ragContext && (
//                     <div ref={ragContextRef} className="rag-context-container w-full max-w-4xl mb-4"> {/* Added width constraints */}
//                         <h3 className="rag-context-heading">Context for Query: <span className="font-normal italic">"{ragContext.query}"</span></h3>
 
//                         {/* Text Context */}
//                         {ragContext.text_context && ragContext.text_context.length > 0 && (
//                             <div className="mb-4">
//                                 <h4 className="rag-context-subheading">Text Sources:</h4>
//                                 <ul className="text-context-list list-disc list-inside space-y-1 text-sm"> {/* Adjusted text size */}
//                                     {ragContext.text_context.map((text, index) => (
//                                         <li key={`text-${index}`}>{text}</li>
//                                     ))}
//                                 </ul>
//                             </div>
//                         )}
 
//                         {/* Image Context - Use filteredImages */}
//                         {filteredImages.length > 0 && ( // Check filtered list length
//                             <div>
//                                 <h4 className="rag-context-subheading">Image Sources:</h4>
//                                 <div className="image-context-grid">
//                                     {filteredImages.map((imgCtx, index) => ( // Map over filtered list
//                                         <div key={`img-${index}`} className="rag-image-item">
//                                             {imgCtx.image_base64 ? (
//                                                 <img
//                                                     src={imgCtx.image_base64}
//                                                     alt={imgCtx.caption || `Context Image ${index + 1}`}
//                                                     className="rag-image-thumbnail"
//                                                     onClick={() => openImageModal(imgCtx.image_base64)}
//                                                 />
//                                             ) : (
//                                                 <div className="rag-image-error">Image unavailable</div>
//                                             )}
//                                             {/* Display Caption */}
//                                             <p className="image-caption">{imgCtx.caption || "No caption"}</p>
//                                             {/* --- DISPLAY FILENAME --- */}
//                                             <p className="image-filename">{imgCtx.file_name || "Unknown file"}</p>
//                                         </div>
//                                     ))}
//                                 </div>
//                             </div>
//                         )}
//                     </div>
//                 )}

      
//     </div>
//   );
// }






// Component:
// {/* RAG Context Display Area */}
             
 
// // RAG context widget to show: detection ->
// //       newWs.addEventListener("message", (event) => {
// //         if (event.data instanceof ArrayBuffer) {
// //             enqueueAudioFromProto(event.data, newAudioContext);
// //         } else if (typeof event.data === 'string') {
// //             try {
// //                 const messageData = JSON.parse(event.data);
// //                 // Check message type
// //                 if (messageData.type === 'log' && messageData.data) {
// //                     addLog(messageData.data); // Add standard log
// //                 } else if (messageData.type === 'rag_context' && messageData.data) {
// //                     console.log("Received RAG Context:", messageData.data);
// //                     const validatedData = {
// //                         ...messageData.data,
// //                         image_context: (messageData.data.image_context || []).map((img: any) => ({
// //                             image_base64: img.image_base64 || null,
// //                             caption: img.caption || "No caption",
// //                             file_name: img.file_name || "Unknown file" // Ensure file_name exists
// //                         }))
// //                     };
// //                     setRagContext(validatedData); // Set RAG context state
// //                     // Optionally add a log message indicating context was received
// //                     addLog({ level: "INFO", time: new Date().toISOString(), message: `RAG context received for query: "${messageData.data.query}..."` });
// //                 } else {
// //                     console.warn("Received unknown text message structure:", messageData);
// //                 }
// //             } catch (e) {
// //                 console.error("Failed to parse text message as JSON:", event.data, e);
// //             }
// //         } else {
// //             console.warn("Received unexpected message type:", typeof event.data);
// //         }
// //     });
 



// import React, { useState, useEffect, useRef } from 'react';

// function RAGContextWidget({ ragContext }) {
//   const [filteredImages, setFilteredImages] = useState([]);
//   const ragContextRef = useRef(null);

//   useEffect(() => {
//     if (ragContext && ragContext.image_context) {
//       const filtered = ragContext.image_context.filter(img => img.image_base64);
//       setFilteredImages(filtered);
//     } else {
//       setFilteredImages([]);
//     }
//   }, [ragContext]);

//   const openImageModal = (imageBase64) => {
//     // For now, just alert or console log. You can implement modal later.
//     alert('Image clicked!');
//   };

//   if (!ragContext) return null;
//  console.log(ragContext, "raggggggg")

//   return (
//     <div ref={ragContextRef} className="w-full max-w-4xl mb-4 bg-gray-700 border border-gray-600 rounded-xl p-4">
//       <h3 className="text-white text-lg font-semibold mb-2">
//         Context for Queryass: <span className="font-normal italic">"{ragContext.query}"</span>
//       </h3>

//       {/* Text Context */}
//       {/* {ragContext.text_context && ragContext.text_context.length > 0 && (
//         <div className="mb-4">
//           <h4 className="text-white font-semibold mb-1">Text Sources:</h4>
//           <ul className="list-disc list-inside space-y-1 text-sm text-gray-300">
//             {ragContext.text_context.map((text, index) => (
//               <li key={`text-${index}`}>{text}</li>
//             ))}
//           </ul>
//         </div>
//       )} */}

//       {/* Image Context */}
//       {filteredImages.length > 0 && (
//         <div>
//           <h4 className="text-white font-semibold mb-1">Image Sources:</h4>
//           <div className="grid grid-cols-3 gap-4">
//             {filteredImages.map((imgCtx, index) => (
//               <div key={`img-${index}`}>
//                 {imgCtx.image_base64 ? (
//                   <img
//                     src={imgCtx.image_base64}
//                     alt={imgCtx.caption || `Context Image ${index + 1}`}
//                     className="rounded shadow-md cursor-pointer"
//                     onClick={() => openImageModal(imgCtx.image_base64)}
//                   />
//                 ) : (
//                   <div className="text-red-500">Image unavailable</div>
//                 )}
//                 <p className="text-gray-300 text-xs mt-1">{imgCtx.caption || 'No caption'}</p>
//                 <p className="text-gray-400 text-xs">{imgCtx.file_name || 'Unknown file'}</p>
//               </div>
//             ))}
//           </div>
//         </div>
//       )}
//     </div>
//   );
// }

// export default RAGContextWidget;












// import React, { useState, useEffect, useRef } from 'react';

// function RAGContextWidget({ ragContext, ragmessage }) {
//   const [filteredImages, setFilteredImages] = useState([]);
//   const ragContextRef = useRef(null);
//   console.log(ragmessage, '222222222222222222');

//   useEffect(() => {
//     if (ragContext && ragContext.image_context) {
//       const filtered = ragContext.image_context.filter(img => img.image_base64);
//       setFilteredImages(filtered);
//     } else {
//       setFilteredImages([]);
//     }
//   }, [ragContext]);

//   const openImageModal = (imageBase64) => {
//     // For now, just alert or console log. You can implement modal later.
//     alert('Image clicked!');
//   };

//   if (!ragContext) return null;

//   return (
//     <div
//       ref={ragContextRef}
//       className="w-full max-w-4xl mb-4 bg-gray-900 border border-gray-600 rounded-xl p-4"
//     >
//       <h3 className="text-white text-lg font-semibold mb-4">
//         Context for Query: <span className="font-normal italic">{`"${ragContext.query}"`}</span>
//       </h3>

//       {/* Text Context */}
//       {/* {ragContext.text_context && ragContext.text_context.length > 0 && (
//         <div className="mb-6">
//           <h4 className="text-white font-semibold mb-2">Text Sources:</h4>
//           <ul className="list-disc list-inside space-y-1 text-sm text-gray-300">
//             {ragContext.text_context.map((text, index) => (
//               <li key={`text-${index}`}>{text}</li>
//             ))}
//           </ul>
//         </div>
//       )} */}

//       {/* Image Context */}
//       {filteredImages.length > 0 && (
//         <div>
//           <h4 className="text-white font-semibold mb-2">Image Sources:</h4>
//           <div className="grid grid-rows-1 sm:grid-rows-2 md:grid-rows-3 gap-6">
//             {filteredImages.map((imgCtx, index) => (
//               <div
//                 key={`img-${index}`}
//                 className="bg-gray-800 rounded-lg shadow p-3 flex flex-col items-center"
//               >
//                 {imgCtx.image_base64 ? (
//                   <img
//                     src={imgCtx.image_base64}
//                     alt={imgCtx.caption || `Context Image ${index + 1}`}
//                     className="w-full object-contain rounded-lg shadow-lg mb-2 cursor-pointer transition-transform duration-200 hover:scale-105"
//                     onClick={() => openImageModal(imgCtx.image_base64)}
//                   />
//                 ) : (
//                   <div className="text-red-500">Image unavailable</div>
//                 )}
//                 <p className="text-gray-300 text-xs mt-1 text-center">{imgCtx.caption || 'No caption'}</p>
//                 <p className="text-gray-400 text-xs text-center">{imgCtx.file_name || 'Unknown file'}</p>
//               </div>
//             ))}
//           </div>
//         </div>
//       )}
//     </div>
//   );
// }

// export default RAGContextWidget;




// import React, { useState, useEffect, useRef } from 'react';

// function RAGContextWidget({ ragContext, ragmessage }) {
//   console.log(ragmessage, "sssssssssssssssssss")
//   const [filteredImages, setFilteredImages] = useState([]);
//   const ragContextRef = useRef(null);

//   useEffect(() => {
//     if (ragContext && ragContext.image_context) {
//       console.log("image eeeeeeeeee", ragContext.image_context )
//       const filtered = ragContext.image_context.filter(img => img.image_base64);
//       console.log("Noooooooooooooooooooooooooo", filtered.length )

//       setFilteredImages(filtered);
//     } else {
//       setFilteredImages([]);
//     }
//   }, [ragContext]);

//   const openImageModal = (imageBase64) => {
//     alert('Image clicked!');
//   };

//   if (!ragContext) return null;

//   return (
//     <div
//       ref={ragContextRef}
//       className="w-full max-w-4xl mb-4 bg-gray-900 border border-gray-600 rounded-xl p-4"
//     >
//       <h3 className="text-white text-lg font-semibold mb-4">
//         Context for Query: <span className="font-normal italic">{`"${ragContext.query}"`}</span>
//       </h3>

//       {/* Image Context */}
//       {filteredImages.length > 0 && (
//         <div>
//           <h4 className="text-white font-semibold mb-2">Image Sources:</h4>
//           <div className="grid grid-rows-1 sm:grid-rows-2 md:grid-rows-3 gap-6">
//             {filteredImages.map((imgCtx, index) => (
//               <div
//                 key={`img-${index}`}
//                 className="bg-gray-800 rounded-lg shadow p-3 flex flex-col items-center"
//               >
//                 {imgCtx.image_base64 ? (
//                   <img
//                     src={imgCtx.image_base64}
//                     alt={imgCtx.caption || `Context Image ${index + 1}`}
//                     className="w-full object-contain rounded-lg shadow-lg mb-2 cursor-pointer transition-transform duration-200 hover:scale-105"
//                     onClick={() => openImageModal(imgCtx.image_base64)}
//                   />
//                 ) : (
//                   <div className="text-red-500">Image unavailable</div>
//                 )}
//                 {/* <p className="text-gray-300 text-xs mt-1 text-center">{imgCtx.caption || 'No caption'}</p>
//                 <p className="text-gray-400 text-xs text-center">{imgCtx.file_name || 'Unknown file'}</p> */}
//               </div>
//             ))}
//           </div>
//         </div>
//       )}

//       {/* Rag Message Below Images */}
//       {ragmessage && (
//         <div className="mt-6 p-4 bg-gray-800 rounded">
//           <h4 className="text-white font-semibold mb-2">Model Answer:</h4>
//           <p className="text-gray-200 text-base">{ragmessage}</p>
//         </div>
//       )}
//     </div>
//   );
// }

// export default RAGContextWidget;


import React, { useState, useEffect, useRef } from 'react';

function RAGContextWidget({ ragContext, ragmessage }) {
  const [filteredImages, setFilteredImages] = useState([]);
  const ragContextRef = useRef(null);

  useEffect(() => {
    if (ragContext && ragContext.image_context) {
      setFilteredImages(ragContext.image_context.filter(img => img.image_base64));
    } else {
      setFilteredImages([]);
    }
  }, [ragContext]);

  const openImageModal = (imageBase64) => {
    alert('Image clicked!');
  };

  if (!ragContext) return null;

  return (
    <div
      ref={ragContextRef}
      className="w-full max-w-4xl bg-gray-900 border border-gray-600 rounded-xl p-4"
    >
      <h3 className="text-white text-lg font-semibold mb-4">
        Context for Query: <span className="font-normal italic">{`"${ragContext.query}"`}</span>
      </h3>

      {/* Text Context */}
      {/* {ragContext.text_context && ragContext.text_context.length > 0 && (
        <div className="mb-6">
          <h4 className="text-white font-semibold mb-2">Text Sources:</h4>
          <ul className="list-disc list-inside space-y-1 text-sm text-gray-300">
            {ragContext.text_context.map((text, index) => (
              <li key={`text-${index}`}>{text}</li>
            ))}
          </ul>
        </div>
      )} */}

      {/* Image Context */}
      {filteredImages.length > 0 && (
        <div>
          <h4 className="text-white font-semibold mb-2">Image Sources:</h4>
          <div className="grid grid-rows-1 sm:grid-rows-2 md:grid-rows-3  mb-1">
            {filteredImages.map((imgCtx, index) => (
              <div
                key={`img-${index}`}
                className="bg-gray-800 rounded-lg shadow flex flex-col items-center"
              >
                {imgCtx.image_base64 ? (
                  <img
                    src={imgCtx.image_base64}
                    alt={imgCtx.caption || `Context Image ${index + 1}`}
                    className="w-full object-contain rounded-lg shadow-lg cursor-pointer transition-transform duration-200 hover:scale-105"
                    onClick={() => openImageModal(imgCtx.image_base64)}
                  />
                ) : (
                  <div className="text-red-500">Image unavailable</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {ragmessage && (
        <div className="p-4 bg-gray-800 rounded">
          <h4 className="text-white font-semibold mb-2">Model Answer:</h4>
          <p className="text-gray-200 text-base">{ragmessage}</p>
        </div>
      )}
    </div>
  );
}

export default RAGContextWidget;
