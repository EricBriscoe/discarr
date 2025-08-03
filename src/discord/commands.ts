import { 
  SlashCommandBuilder, 
  CommandInteraction, 
  EmbedBuilder 
} from 'discord.js';
import { RadarrClient } from '../services/radarr-client';
import { SonarrClient } from '../services/sonarr-client';

export interface SlashCommand {
  data: SlashCommandBuilder;
  execute: (interaction: CommandInteraction) => Promise<void>;
}

export class CleanupCommand implements SlashCommand {
  data = new SlashCommandBuilder()
    .setName('cleanup')
    .setDescription('Remove all importBlocked items from Radarr and Sonarr queues');

  private radarrClient: RadarrClient;
  private sonarrClient: SonarrClient;

  constructor(radarrClient: RadarrClient, sonarrClient: SonarrClient) {
    this.radarrClient = radarrClient;
    this.sonarrClient = sonarrClient;
  }

  async execute(interaction: CommandInteraction): Promise<void> {
    await interaction.deferReply();

    try {
      const embed = new EmbedBuilder()
        .setTitle('🧹 Cleanup in Progress')
        .setDescription('Scanning for importBlocked items...')
        .setColor(0xffaa00)
        .setTimestamp();

      await interaction.editReply({ embeds: [embed] });

      // Get all importBlocked items from both services
      const [radarrBlocked, sonarrBlocked] = await Promise.all([
        this.radarrClient.getImportBlockedItems(),
        this.sonarrClient.getImportBlockedItems()
      ]);

      if (radarrBlocked.length === 0 && sonarrBlocked.length === 0) {
        embed
          .setTitle('🧹 Cleanup Complete')
          .setDescription('No importBlocked items found.')
          .setColor(0x00ff00);
        
        await interaction.editReply({ embeds: [embed] });
        return;
      }

      // Update embed with found items
      embed
        .setDescription(`Found ${radarrBlocked.length} Radarr and ${sonarrBlocked.length} Sonarr importBlocked items.\nRemoving...`)
        .setColor(0xff6600);

      await interaction.editReply({ embeds: [embed] });

      // Remove all blocked items
      const [radarrResults, sonarrResults] = await Promise.all([
        this.radarrClient.removeQueueItems(radarrBlocked.map(item => item.id)),
        this.sonarrClient.removeQueueItems(sonarrBlocked.map(item => item.id))
      ]);

      // Calculate success/failure counts
      const radarrSuccess = radarrResults.filter(r => r.success).length;
      const radarrFailed = radarrResults.length - radarrSuccess;
      const sonarrSuccess = sonarrResults.filter(r => r.success).length;
      const sonarrFailed = sonarrResults.length - sonarrSuccess;

      // Create final result embed
      const resultEmbed = new EmbedBuilder()
        .setTitle('🧹 Cleanup Complete')
        .setTimestamp()
        .setColor(radarrFailed === 0 && sonarrFailed === 0 ? 0x00ff00 : 0xff6600);

      let description = '';
      if (radarrSuccess > 0) {
        description += `✅ Removed ${radarrSuccess} Radarr item${radarrSuccess !== 1 ? 's' : ''}\n`;
      }
      if (sonarrSuccess > 0) {
        description += `✅ Removed ${sonarrSuccess} Sonarr item${sonarrSuccess !== 1 ? 's' : ''}\n`;
      }
      if (radarrFailed > 0) {
        description += `❌ Failed to remove ${radarrFailed} Radarr item${radarrFailed !== 1 ? 's' : ''}\n`;
      }
      if (sonarrFailed > 0) {
        description += `❌ Failed to remove ${sonarrFailed} Sonarr item${sonarrFailed !== 1 ? 's' : ''}\n`;
      }

      resultEmbed.setDescription(description.trim());
      await interaction.editReply({ embeds: [resultEmbed] });

    } catch (error) {
      console.error('Cleanup command error:', error);
      
      const errorEmbed = new EmbedBuilder()
        .setTitle('🧹 Cleanup Failed')
        .setDescription(`An error occurred during cleanup: ${error instanceof Error ? error.message : 'Unknown error'}`)
        .setColor(0xff0000)
        .setTimestamp();

      await interaction.editReply({ embeds: [errorEmbed] });
    }
  }
}