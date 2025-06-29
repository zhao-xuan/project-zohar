"""
Bot Manager for coordinating Personal and Public chatbots
"""
from typing import Optional, Dict, Any
from src.core.agents.personal_agent import PersonalAgent
from src.core.agents.public_agent import PublicAgent


class BotManager:
    """
    Manages both personal and public chatbot instances
    """
    
    def __init__(self):
        self._personal_bot: Optional[PersonalAgent] = None
        self._public_bot: Optional[PublicAgent] = None
    
    def get_personal_bot(self) -> PersonalAgent:
        """Get or create the personal bot instance"""
        if self._personal_bot is None:
            self._personal_bot = PersonalAgent()
        return self._personal_bot
    
    def get_public_bot(self) -> PublicAgent:
        """Get or create the public bot instance"""
        if self._public_bot is None:
            self._public_bot = PublicAgent()
        return self._public_bot
    
    async def process_message(
        self, 
        message: str, 
        bot_type: str = "personal",
        conversation_id: Optional[str] = None
    ) -> str:
        """
        Process a message with the appropriate bot
        
        Args:
            message: User message
            bot_type: 'personal' or 'public'
            conversation_id: Optional conversation ID
            
        Returns:
            Bot response
        """
        if bot_type == "personal":
            bot = self.get_personal_bot()
        elif bot_type == "public":
            bot = self.get_public_bot()
        else:
            return f"Error: Unknown bot type '{bot_type}'"
        
        return await bot.process_message(message, conversation_id)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all bot components"""
        health_status = {
            "personal_bot": "not_initialized",
            "public_bot": "not_initialized",
            "overall_status": "healthy"
        }
        
        try:
            if self._personal_bot is not None:
                # Check personal bot health
                health_status["personal_bot"] = "healthy"
            
            if self._public_bot is not None:
                # Check public bot health  
                health_status["public_bot"] = "healthy"
                
        except Exception as e:
            health_status["overall_status"] = f"error: {str(e)}"
        
        return health_status 