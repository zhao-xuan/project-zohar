"""
Ollama Service for local LLM interaction
"""
import json
import asyncio
from typing import Dict, Any, Optional, List
import httpx
from rich.console import Console

from src.config.settings import settings

console = Console()


class OllamaService:
    """
    Service for interacting with local Ollama instance running DeepSeek model
    """
    
    def __init__(self):
        self.host = settings.llm.ollama_host
        self.model = settings.llm.model_name
        self.max_tokens = settings.llm.max_tokens
        self.temperature = settings.llm.temperature
        self.timeout = 60  # Longer timeout for LLM requests
    
    async def is_available(self) -> bool:
        """
        Check if Ollama is running and the model is available
        
        Returns:
            True if Ollama and model are available
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Check if Ollama is running
                response = await client.get(f"{self.host}/api/tags")
                if response.status_code != 200:
                    return False
                
                # Check if DeepSeek model is available
                models = response.json().get("models", [])
                model_names = [model.get("name", "") for model in models]
                
                # Try exact match first, then partial match
                if self.model in model_names:
                    return True
                
                # For partial matches (e.g., "deepseek" should match "deepseek-r1:70b")
                model_base = self.model.split(":")[0]
                for model_name in model_names:
                    if model_name.startswith(model_base):
                        console.print(f"[green]Found compatible model: {model_name} for {self.model}[/green]")
                        return True
                
                return False
                
        except Exception as e:
            console.print(f"[yellow]Ollama not available: {e}[/yellow]")
            return False
    
    async def pull_model(self) -> bool:
        """
        Pull the DeepSeek model if not available
        
        Returns:
            True if model was pulled successfully
        """
        try:
            console.print(f"🔄 Pulling {self.model} model...")
            
            async with httpx.AsyncClient(timeout=300) as client:  # 5-minute timeout for pulling
                response = await client.post(
                    f"{self.host}/api/pull",
                    json={"name": self.model}
                )
                
                if response.status_code == 200:
                    console.print(f"✅ {self.model} model pulled successfully")
                    return True
                else:
                    console.print(f"❌ Failed to pull {self.model} model: {response.text}")
                    return False
                    
        except Exception as e:
            console.print(f"❌ Error pulling model: {e}")
            return False
    
    async def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Generate a response using the local DeepSeek model
        
        Args:
            prompt: User prompt/question
            system_prompt: System instructions
            context: Additional context
            
        Returns:
            Generated response
        """
        try:
            # Build the full prompt
            full_prompt = ""
            
            if system_prompt:
                full_prompt += f"System: {system_prompt}\n\n"
            
            if context:
                full_prompt += f"Context: {context}\n\n"
            
            full_prompt += f"User: {prompt}\n\nAssistant:"
            
            # Make request to Ollama
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens
                        },
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "No response generated")
                else:
                    return f"Error: Ollama request failed with status {response.status_code}"
                    
        except httpx.TimeoutException:
            return "Error: Request timed out. The model might be processing a complex request."
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    async def generate_tool_response(
        self, 
        tool_category: str, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> str:
        """
        Generate a tool response using DeepSeek model
        
        Args:
            tool_category: Category of tool (email, browser, system)
            tool_name: Name of the tool
            parameters: Tool parameters
            
        Returns:
            Generated tool response
        """
        
        # Create a specialized prompt for tool responses
        system_prompt = f"""You are a helpful assistant that simulates the execution of tools for a personal chatbot system.

Tool Category: {tool_category}
Tool Name: {tool_name}
Parameters: {json.dumps(parameters, indent=2)}

Please provide a realistic response as if you actually executed this tool. Be specific and helpful.

For email tools: Mention specific details like email addresses, subjects, and brief content summaries.
For browser tools: Provide realistic web content or search results.
For system tools: Give realistic file system or command execution results.

Keep responses concise but informative. Always start your response with a brief action confirmation."""

        prompt = f"Execute the {tool_name} tool in the {tool_category} category with the given parameters."
        
        return await self.generate_response(prompt, system_prompt)
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Chat completion interface similar to OpenAI API
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system_prompt: Optional system prompt
            
        Returns:
            Generated response
        """
        
        # Convert messages to a single prompt
        prompt_parts = []
        
        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}")
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt_parts.append("Assistant:")
        full_prompt = "\n\n".join(prompt_parts)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens
                        },
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "No response generated")
                else:
                    return f"Error: Chat completion failed with status {response.status_code}"
                    
        except Exception as e:
            return f"Error in chat completion: {str(e)}"
    
    async def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model
        
        Returns:
            Model information dictionary
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.host}/api/show",
                    json={"name": self.model}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Failed to get model info: {response.status_code}"}
                    
        except Exception as e:
            return {"error": f"Error getting model info: {str(e)}"}
    
    async def list_models(self) -> List[str]:
        """
        List all available models in Ollama
        
        Returns:
            List of model names
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.host}/api/tags")
                
                if response.status_code == 200:
                    models_data = response.json().get("models", [])
                    return [model.get("name", "") for model in models_data]
                else:
                    return []
                    
        except Exception as e:
            console.print(f"Error listing models: {e}")
            return []


# Global Ollama service instance
ollama_service = OllamaService() 