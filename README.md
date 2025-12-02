# **Self-Hosted AI Model (LlaMA 3) with Python + FastAPI and React.js for frontend**

### Clone or fork the project and CD to the project directory
On your terminal run command below to build the project

```bash
docker compose up -d --build
```

Pull LLaMA 3 AI model (by default this will pull the model with 8b parameters)
```bash
docker exec -it ollama-cpu ollama pull llama3
```

Check if LlaMA is installed
```bash
docker exec -it ollama-cpu bash
ollama lists
```
you should see something like this
```text
NAME             ID         SIZE      MODIFIED   
llama3:latest    ...        ...       ....
```

Test your AI, on your terminal run:
```bash
curl -X POST http://localhost:8002/generate \
  -H "X-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is the latest tech as of this year?", "model": "llama3"}'
```

- Replace `your_api_key` with your own generated key

### On the project directory create your react frontend app
Install the following packages:

```text
- tailwindcss
- lucide-react
- react-markdown
- remark-gfm
```

Here's the snipaste of the Chat UI

```jsx
import { Globe, Paperclip, Plus, Send } from 'lucide-react';
import Layout from '../Layout';
import { useEffect, useRef, useState } from 'react';
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const Chats = () => {
  const [prompt, setPrompt] = useState<string | null>(null);
  const promptRef = useRef<HTMLDivElement>(null);
  const [messages, setMessages] = useState<{ sender: "user" | "ai"; text: string }[]>([]);
  const [partialMessage, setPartialMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    console.log('object', prompt)
    if (!prompt || !prompt.trim() || !promptRef.current) return;

    setMessages(prev => [...prev, { sender: "user", text: prompt }]);
    setPartialMessage("");
    setLoading(true);
    promptRef.current.innerText = ''

    try {
      const response = await fetch("http://localhost:8002/generate", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "X-API-KEY": 'your_own_api_key'
        },
        body: JSON.stringify({ prompt: prompt, model: 'llama3' }),
      });

      setPrompt(null);
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let accumulated = ""; // store all chunks locally

      while (!done && reader) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          const chunk = decoder.decode(value, { stream: true }); // keep UTF-8 safe
          accumulated += chunk;
          setPartialMessage(accumulated); // update live typing
        }
      }

      // decode any remaining bytes
      accumulated += decoder.decode(); 

      // Once done, push AI message to messages and clear partial
      setMessages(prev => [...prev, { sender: "ai", text: accumulated }]);
      setPartialMessage("");

    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { sender: "ai", text: "Error: could not get response." }]);
      setPrompt(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log(messages, partialMessage)
  }, [messages, partialMessage])

  return (
    <div className='flex items-center justify-center min-h-[calc(100vh-120px)] w-7/12 mx-auto mt-4 text-sm'>
      <div className='relative w-full'>
        <div className={`flex flex-col space-y-4 mb-[50px] ai-response`}>
          {messages.map((msg, idx) => (
            <div key={idx} className={`${msg.sender === 'user' ? 'flex justify-end' : 'max-w-12/12 overflow-auto'}`}>
              {(() => {
                if (msg.sender === "user") {
                  return (
                    <div className='max-w-9/12 py-2 px-3 rounded-xl text-sm bg-indigo-100 whitespace-pre-wrap'>
                      {msg.text}
                    </div>
                  )
                }
                return (
                  <div className='max-w-12/12 overflow-auto'>
                    <Markdown remarkPlugins={[remarkGfm]}>{partialMessage}</Markdown>
                  </div>
                )
              })()}
            </div>
          ))}

          {loading && !partialMessage && <div className="text-gray-400">Thinking ...</div>}
          {partialMessage && <Markdown remarkPlugins={[remarkGfm]}>{partialMessage}</Markdown>}
        </div>
        <div className='sticky bottom-0 pt-2 pb-6 bg-white'>
          <div className='max-h-fit min-w-fit border px-2 pt-4 pb-2 border-gray-300 bg-white rounded-2xl'>

            <div className="relative w-full px-2">
              {(!promptRef?.current?.innerText || !prompt) && (
                <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none font-normal">
                 Chat with AI
                </span>
              )}

              <div
                ref={promptRef}
                contentEditable
                className="w-full focus:outline-none max-h-[200px] overflow-auto whitespace-pre-wrap"
                suppressContentEditableWarning={true}
                onInput={() => {
                  const el = promptRef.current;
                  if (!el) return;

                  const text = el.innerText.trim();
                  setPrompt(text);
                }}
                onPaste={(e) => {
                  e.preventDefault();
                  const text = e.clipboardData.getData("text/plain");
                  document.execCommand("insertText", false, text);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && e.shiftKey && prompt) {
                    // setIsNextLine(true);
                    return;
                  }

                  if (e.key === "Enter") {
                    handleSubmit();
                    e.preventDefault();
                  }
                }}
              />
            </div>
            
            <div className='flex items-center justify-between mt-5 bg-white'>
              <div className='flex items-center gap-1 text-[13px]'>
                <button
                  className='hidden h-9 min-w-9 items-center justify-center border border-gray-100 hover:border-gray-200 rounded-full bg-gray-100 hover:bg-gray-200 cursor-pointer'
                >
                  <Plus className='size-5' />
                </button>
                <button
                  className='h-9 flex items-center justify-center gap-2 px-3 border border-gray-100 hover:border-gray-200 rounded-full bg-gray-100 hover:bg-gray-200 cursor-pointer'
                >
                  <Paperclip className='size-4' />
                  Attach
                </button>
                <button 
                  className='h-9 flex items-center justify-center gap-2 px-3 border border-gray-100 hover:border-gray-200 rounded-full bg-gray-100 hover:bg-gray-200 cursor-pointer'
                >
                  <Globe className='size-4' />
                  Web search
                </button>
              </div>
              <button 
                className='h-9 min-w-9 flex items-center justify-center border border-indigo-500 rounded-full bg-indigo-500 hover:bg-indigo-600 text-white cursor-pointer'
                onClick={() => handleSubmit()}
              >
                <Send className='size-4' />
              </button>
            </div>

          </div>

          <div className='flex items-baseline justify-center mt-4 text-gray-500 text-[13px]'>
            Powered by: 
            <span>
              <img
                className="relative top-0.5 opacity-80"
                src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAMAAABF0y+mAAAAWlBMVEVHcEz////////////////////////////9/f3///80NDQAAAD///8AAADs7Ow7OzvIyMiYmJi6urp9fX1nZ2cVFRV2dnYkJCTX19eioqKrq6uJiYlYWFhvb2/EoWB9AAAADHRSTlMAF4eGM2A+5vPC4Berj2PGAAABO0lEQVQokY2Ty4KDIAxFUduibcJDEMV2/v83JyGoZVaTBUQuxMMFlDri1k8aQE/DTf2N+whnjPdG6mjNqVKiu0t70NCCs2gzLtQ+vjW/eBQRKb3UjoesB9zAGNgQvOURqazL/BnWiBRxpcI8ogsnVNGiN8ajrSIws1Bau6DjxOFirVDT3iviZz9o908Fv6mBO4MevsKj4a5XE3fvFZpY39xOwkobAZo8OjeWRDajlczMBOIyhoB5I7AslURMFkyaLZtg50RNElELEPEFBz8BXGB2I2UL0EbWwZ54Zcr1k4H6QlsA4hrCGgtgoR3EhBjKP4xzpR6EKCYU+2Jq95mi2FeM90srlhO91yMzuH9rO9Pq87CPO1K95zPrjmvisC1LJl2XKNtWtPnUlHo9W/H5+u+lLs9hkOfQX8/hFxBNIMRj1sGVAAAAAElFTkSuQmCC"
                style={{ height: "20px", width: "20px"}}
                alt=""
              />
              </span>LLaMA 3
            </div>
        </div>
      </div>
    </div>
  )
}

export default Chats

```

On your frontend `index.css` copy and paste css below

```css
.whitespace-pre-wrap {
  white-space: pre-wrap;
  word-wrap: break-word;
}

.ai-response pre {
  color: #fff;
  background-color: rgb(62, 60, 60);
  padding: 10px 15px;
  border-radius: 15px;
  margin: 10px 0;
}

.ai-response pre code {
  background-color: transparent;
}

.ai-response code:not(pre code) {
  background-color: #e0e0e0;
  padding: 2px 4px;
  border-radius: 5px;
}

.ai-response p {
  line-height: 1.7;
}
```

### Change the setup to however you want that suits your needs.

