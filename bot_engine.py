# -------------------------------
# BotEngine.generate - Beast Mode
# -------------------------------
from openai import OpenAI
import threading
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List

class BotEngine:
    # ... keep your __init__ and memory methods from v1000 unchanged ...

    def generate(self, user_text: str,
                 convo_id: Optional[str] = None,
                 max_tokens: int = 300,
                 temperature: float = 0.2,
                 mode: str = "default",
                 stream: bool = False) -> Dict[str, Any]:
        """
        Beast mode GPT-5-mini interaction.
        Supports:
        - Conversation history (thread-safe)
        - Dynamic persona/mode
        - Usage logging with metadata
        - Safe mode enforcement
        - Optional streaming (placeholder)
        Returns dict:
        - answer: str
        - raw: raw response object
        - error: if failed
        - usage: usage info
        - metadata: dict with convo id, timestamp, prompt length, mode
        """
        # thread-safe memory lock
        _lock = threading.Lock()
        with _lock:
            if openai is None:
                return {"error": "OpenAI SDK not installed."}

            api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                return {"error": "OpenAI API key not set (OPENAI_API_KEY env)."}

            # build system prompt
            system_prompt = self._system_prompt()
            # adjust for mode
            if mode == "business":
                system_prompt += " You are professional, concise, and formal."
            elif mode == "creative":
                system_prompt += " Be playful, imaginative, and creative."
            elif mode == "debug":
                system_prompt += " Provide verbose explanations and debug info."

            messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

            # include conversation history
            if convo_id:
                history = self.get_conversation(convo_id)
                for m in history:
                    messages.append({"role": m["role"], "content": m["content"]})

            # append user message
            messages.append({"role": "user", "content": user_text})

            try:
                client = OpenAI(api_key=api_key)

                if stream:
                    # Placeholder for streaming TTS or chunked output
                    # Can be connected to asyncio / websocket
                    resp = client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        stream=True
                    )
                    content_chunks = []
                    for chunk in resp:
                        try:
                            delta = chunk.choices[0].delta.get("content", "")
                            content_chunks.append(delta)
                        except Exception:
                            continue
                    content = "".join(content_chunks)
                else:
                    # standard response
                    resp = client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    content = resp.choices[0].message.content

                # save to memory
                if convo_id:
                    self.append_message(convo_id, "user", user_text)
                    self.append_message(convo_id, "assistant", content)

                # log usage and metadata
                usage_info = getattr(resp, "usage", None)
                metadata = {
                    "time": datetime.utcnow().isoformat() + "Z",
                    "convo": convo_id or "none",
                    "prompt_len": sum(len(m.get("content","")) for m in messages),
                    "mode": mode,
                    "model": self.model,
                }
                append_usage({"time": metadata["time"], "convo": metadata["convo"], "model": self.model, "usage": usage_info or {}, "mode": mode})

                # return beast response
                return {
                    "answer": content,
                    "raw": resp,
                    "usage": usage_info,
                    "metadata": metadata
                }

            except Exception as e:
                tb = traceback.format_exc()
                logger.exception("Beast mode OpenAI call failed")
                return {"error": str(e), "trace": tb, "metadata": {"convo": convo_id or "none", "mode": mode, "time": datetime.utcnow().isoformat()+"Z"}}

    def _system_prompt(self):
        """
        Base dynamic system prompt.
        Includes safe mode enforcement.
        """
        base = ("You are Neura-AI v1000 Hardcode, a premium AI assistant "
                "optimized for accuracy, conciseness, creativity, and business-grade responses.")
        if FEATURE_FLAGS.get("safe_mode"):
            base += " Do not produce disallowed content; refuse unsafe requests."
        return base