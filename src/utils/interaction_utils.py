"""
Utility functions for handling Discord interactions robustly.
"""
import logging
import discord
from typing import Optional

logger = logging.getLogger(__name__)


async def safe_defer_interaction(interaction: discord.Interaction, ephemeral: bool = True) -> bool:
    """
    Safely defer a Discord interaction with proper error handling.
    
    Args:
        interaction: Discord interaction object
        ephemeral: Whether the response should be ephemeral
        
    Returns:
        bool: True if defer was successful, False otherwise
    """
    try:
        # Check if interaction has already been responded to
        if interaction.response.is_done():
            logger.warning("Interaction has already been responded to")
            return False
            
        await interaction.response.defer(ephemeral=ephemeral)
        logger.debug("Successfully deferred interaction")
        return True
        
    except discord.errors.NotFound as e:
        if e.code == 10062:  # Unknown interaction
            logger.error("Interaction token expired or invalid (10062)")
        else:
            logger.error(f"Interaction not found: {e}")
        return False
        
    except discord.errors.HTTPException as e:
        logger.error(f"HTTP error while deferring interaction: {e}")
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error while deferring interaction: {e}", exc_info=True)
        return False


async def safe_send_response(interaction: discord.Interaction, content: Optional[str] = None, embed: Optional[discord.Embed] = None, ephemeral: bool = True) -> bool:
    """
    Safely send a response to a Discord interaction with fallback handling.
    
    Args:
        interaction: Discord interaction object
        content: Text content to send
        embed: Embed to send
        ephemeral: Whether the response should be ephemeral
        
    Returns:
        bool: True if response was sent successfully, False otherwise
    """
    try:
        # Try to send via followup if interaction was deferred
        if interaction.response.is_done():
            if content and embed:
                await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral)
            elif content:
                await interaction.followup.send(content=content, ephemeral=ephemeral)
            elif embed:
                await interaction.followup.send(embed=embed, ephemeral=ephemeral)
            else:
                await interaction.followup.send("Command completed.", ephemeral=ephemeral)
        else:
            # Try to send initial response
            if content and embed:
                await interaction.response.send_message(content=content, embed=embed, ephemeral=ephemeral)
            elif content:
                await interaction.response.send_message(content=content, ephemeral=ephemeral)
            elif embed:
                await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            else:
                await interaction.response.send_message("Command completed.", ephemeral=ephemeral)
                
        logger.debug("Successfully sent interaction response")
        return True
        
    except discord.errors.NotFound as e:
        if e.code == 10062:  # Unknown interaction
            logger.error("Cannot send response - interaction token expired or invalid (10062)")
        else:
            logger.error(f"Interaction not found when sending response: {e}")
        return False
        
    except discord.errors.HTTPException as e:
        logger.error(f"HTTP error while sending response: {e}")
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error while sending response: {e}", exc_info=True)
        return False


async def handle_interaction_error(interaction: discord.Interaction, error_message: str, ephemeral: bool = True):
    """
    Handle interaction errors by attempting to send an error message.
    
    Args:
        interaction: Discord interaction object
        error_message: Error message to send to user
        ephemeral: Whether the error message should be ephemeral
    """
    try:
        # Create error embed
        embed = discord.Embed(
            title="❌ Command Error",
            description=error_message,
            color=discord.Color.red()
        )
        
        # Try to send error response
        success = await safe_send_response(interaction, embed=embed, ephemeral=ephemeral)
        
        if not success:
            logger.error(f"Failed to send error message to user: {error_message}")
            
    except Exception as e:
        logger.error(f"Failed to handle interaction error: {e}", exc_info=True)


def has_admin_permissions(interaction: discord.Interaction) -> bool:
    """
    Check if the user has administrator permissions in the guild.
    
    Args:
        interaction: Discord interaction object
        
    Returns:
        bool: True if user has admin permissions, False otherwise
    """
    try:
        # Check if we're in a guild
        if not interaction.guild:
            return False
            
        # Try to access guild_permissions (works if user is a Member object)
        try:
            return interaction.user.guild_permissions.administrator  # type: ignore
        except AttributeError:
            # Fallback: check if user is guild owner
            return str(interaction.user.id) == str(interaction.guild.owner_id)
        
    except Exception as e:
        logger.error(f"Error checking admin permissions: {e}")
        return False


def is_guild_owner(interaction: discord.Interaction) -> bool:
    """
    Check if the user is the guild owner.
    
    Args:
        interaction: Discord interaction object
        
    Returns:
        bool: True if user is guild owner, False otherwise
    """
    try:
        if not interaction.guild:
            return False
        return str(interaction.user.id) == str(interaction.guild.owner_id)
    except Exception as e:
        logger.error(f"Error checking guild owner: {e}")
        return False
