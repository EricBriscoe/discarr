import { 
  SlashCommandBuilder, 
  CommandInteraction, 
  EmbedBuilder 
} from 'discord.js';
import { QBittorrentClient } from '../services/qbittorrent-client.js';

export interface SlashCommand {
  data: SlashCommandBuilder;
  execute: (interaction: CommandInteraction) => Promise<void>;
}

export class CleanupCommand implements SlashCommand {
  data = new SlashCommandBuilder()
    .setName('cleanup')
    .setDescription('Remove seeding/stalled/stuck torrents with sonarr/radarr labels from qBittorrent');

  private qbittorrentClient: QBittorrentClient;

  constructor(qbittorrentClient: QBittorrentClient) {
    this.qbittorrentClient = qbittorrentClient;
  }

  async execute(interaction: CommandInteraction): Promise<void> {
    await interaction.deferReply();

    try {
      const embed = new EmbedBuilder()
        .setTitle('🧹 Cleanup in Progress')
        .setDescription('Scanning qBittorrent for seeding/stalled/stuck torrents with sonarr/radarr labels...')
        .setColor(0xffaa00)
        .setTimestamp();

      await interaction.editReply({ embeds: [embed] });

      // Get torrents to remove from qBittorrent
      const torrentsToRemove = await this.qbittorrentClient.getSeedinOrStalledTorrentsWithLabels();

      if (torrentsToRemove.length === 0) {
        embed
          .setTitle('🧹 Cleanup Complete')
          .setDescription('No seeding/stalled/stuck torrents with sonarr/radarr labels found.')
          .setColor(0x00ff00);
        
        await interaction.editReply({ embeds: [embed] });

        // Delete the no-items message after 3 seconds
        setTimeout(async () => {
          try {
            await interaction.deleteReply();
          } catch (error) {
            console.error('Failed to delete cleanup message:', error);
          }
        }, 3000);
        return;
      }

      // Update embed with found items
      let updateDescription = `Found ${torrentsToRemove.length} torrent${torrentsToRemove.length !== 1 ? 's' : ''} to clean up:\n`;
      updateDescription += torrentsToRemove.slice(0, 5).map(t => `• ${t.name} (${t.category}/${t.state})`).join('\n');
      if (torrentsToRemove.length > 5) {
        updateDescription += `\n• ...and ${torrentsToRemove.length - 5} more`;
      }
      updateDescription += `\n\nRemoving from qBittorrent and disk...`;

      embed
        .setDescription(updateDescription)
        .setColor(0xff6600);

      await interaction.editReply({ embeds: [embed] });

      // Remove torrents from qBittorrent
      const results = await this.qbittorrentClient.deleteTorrents(
        torrentsToRemove.map(t => t.hash), 
        true // Delete files from disk
      );

      // Calculate success/failure counts
      const successful = results.filter(r => r.success).length;
      const failed = results.length - successful;

      // Create final result embed
      const resultEmbed = new EmbedBuilder()
        .setTitle('🧹 Cleanup Complete')
        .setTimestamp()
        .setColor(failed === 0 ? 0x00ff00 : 0xff6600);

      let resultDescription = '';
      if (successful > 0) {
        resultDescription += `✅ Removed ${successful} torrent${successful !== 1 ? 's' : ''} from qBittorrent and disk\n`;
      }
      if (failed > 0) {
        resultDescription += `❌ Failed to remove ${failed} torrent${failed !== 1 ? 's' : ''}\n`;
      }

      resultEmbed.setDescription(resultDescription.trim());
      await interaction.editReply({ embeds: [resultEmbed] });

      // Delete the cleanup message after 5 seconds to keep channel clean
      setTimeout(async () => {
        try {
          await interaction.deleteReply();
        } catch (error) {
          console.error('Failed to delete cleanup message:', error);
        }
      }, 5000);

    } catch (error) {
      console.error('Cleanup command error:', error);
      
      const errorEmbed = new EmbedBuilder()
        .setTitle('🧹 Cleanup Failed')
        .setDescription(`An error occurred during cleanup: ${error instanceof Error ? error.message : 'Unknown error'}`)
        .setColor(0xff0000)
        .setTimestamp();

      await interaction.editReply({ embeds: [errorEmbed] });

      // Delete error message after 10 seconds
      setTimeout(async () => {
        try {
          await interaction.deleteReply();
        } catch (error) {
          console.error('Failed to delete cleanup error message:', error);
        }
      }, 10000);
    }
  }
}