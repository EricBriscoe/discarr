import { 
  SlashCommandBuilder, 
  ChatInputCommandInteraction, 
  EmbedBuilder,
  ActionRowBuilder,
  StringSelectMenuBuilder,
  StringSelectMenuOptionBuilder,
  ComponentType,
  SlashCommandOptionsOnlyBuilder
} from 'discord.js';
import { QBittorrentClient } from '../services/qbittorrent-client.js';
import { SonarrClient } from '../services/sonarr-client.js';

export interface SlashCommand {
  data: SlashCommandBuilder | SlashCommandOptionsOnlyBuilder;
  execute: (interaction: ChatInputCommandInteraction) => Promise<void>;
}

export class CleanupCommand implements SlashCommand {
  data = new SlashCommandBuilder()
    .setName('cleanup')
    .setDescription('Remove seeding/stalled/stuck torrents with sonarr/radarr labels from qBittorrent');

  private qbittorrentClient: QBittorrentClient;

  constructor(qbittorrentClient: QBittorrentClient) {
    this.qbittorrentClient = qbittorrentClient;
  }

  async execute(interaction: ChatInputCommandInteraction): Promise<void> {
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

export class CalendarCommand implements SlashCommand {
  data = new SlashCommandBuilder()
    .setName('calendar')
    .setDescription('Show upcoming TV episodes for the next week')
    .addIntegerOption(option =>
      option.setName('days')
        .setDescription('Number of days to look ahead (1-14)')
        .setMinValue(1)
        .setMaxValue(14)
        .setRequired(false)
    );

  private sonarrClient: SonarrClient;

  constructor(sonarrClient: SonarrClient) {
    this.sonarrClient = sonarrClient;
  }

  async execute(interaction: ChatInputCommandInteraction): Promise<void> {
    await interaction.deferReply();

    try {
      const days = interaction.options.get('days')?.value as number || 7;
      
      const episodes = await this.sonarrClient.getCalendarEpisodes(days);

      if (episodes.length === 0) {
        const embed = new EmbedBuilder()
          .setTitle('📅 No Upcoming Episodes')
          .setDescription(`No episodes scheduled for the next ${days} day${days !== 1 ? 's' : ''}.`)
          .setColor(0x666666)
          .setTimestamp();

        await interaction.editReply({ embeds: [embed] });
        return;
      }

      // Group episodes by date
      const episodesByDate = new Map<string, typeof episodes>();
      episodes.forEach(episode => {
        if (episode.airDateUtc) {
          const date = new Date(episode.airDateUtc).toDateString();
          if (!episodesByDate.has(date)) {
            episodesByDate.set(date, []);
          }
          episodesByDate.get(date)!.push(episode);
        }
      });

      const embed = new EmbedBuilder()
        .setTitle(`📅 Upcoming Episodes (Next ${days} Days)`)
        .setColor(0x0099ff)
        .setTimestamp();

      let description = '';
      let totalShown = 0;
      const maxEpisodes = 20;

      for (const [date, dayEpisodes] of episodesByDate) {
        if (totalShown >= maxEpisodes) break;
        
        const dateObj = new Date(date);
        const isToday = dateObj.toDateString() === new Date().toDateString();
        const isTomorrow = dateObj.toDateString() === new Date(Date.now() + 86400000).toDateString();
        
        let dateLabel = date;
        if (isToday) dateLabel = '**Today**';
        else if (isTomorrow) dateLabel = '**Tomorrow**';

        description += `\n**${dateLabel}**\n`;

        for (const episode of dayEpisodes.slice(0, maxEpisodes - totalShown)) {
          const hasFileIcon = episode.hasFile ? '✅' : '📺';
          const monitorIcon = episode.monitored ? '' : '🔇';
          const time = episode.airDateUtc ? new Date(episode.airDateUtc).toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit',
            timeZoneName: 'short'
          }) : '';
          
          description += `${hasFileIcon}${monitorIcon} **${episode.seriesTitle}** S${episode.seasonNumber.toString().padStart(2, '0')}E${episode.episodeNumber.toString().padStart(2, '0')}`;
          if (episode.title && episode.title !== 'TBA') {
            description += ` - ${episode.title}`;
          }
          if (time) {
            description += ` (${time})`;
          }
          if (episode.network) {
            description += ` • ${episode.network}`;
          }
          description += '\n';
          totalShown++;
        }
      }

      if (episodes.length > maxEpisodes) {
        description += `\n*...and ${episodes.length - maxEpisodes} more episodes*`;
      }

      embed.setDescription(description);
      embed.setFooter({ text: '✅ Downloaded • 📺 Airing • 🔇 Unmonitored' });

      await interaction.editReply({ embeds: [embed] });

    } catch (error) {
      console.error('Calendar command error:', error);
      
      const errorEmbed = new EmbedBuilder()
        .setTitle('📅 Calendar Error')
        .setDescription(`Failed to fetch calendar: ${error instanceof Error ? error.message : 'Unknown error'}`)
        .setColor(0xff0000)
        .setTimestamp();

      await interaction.editReply({ embeds: [errorEmbed] });
    }
  }
}

export class SeriesSearchCommand implements SlashCommand {
  data = new SlashCommandBuilder()
    .setName('series-search')
    .setDescription('Search for missing episodes for a specific series')
    .addStringOption(option =>
      option.setName('series')
        .setDescription('Series name to search for missing episodes')
        .setRequired(true)
        .setAutocomplete(true)
    );

  private sonarrClient: SonarrClient;

  constructor(sonarrClient: SonarrClient) {
    this.sonarrClient = sonarrClient;
  }

  async execute(interaction: ChatInputCommandInteraction): Promise<void> {
    await interaction.deferReply();

    try {
      const seriesName = interaction.options.get('series')?.value as string;
      
      // Get all series to find the one that matches
      const allSeries = await this.sonarrClient.getSeriesList();
      const matchedSeries = allSeries.find(s => 
        s.title.toLowerCase().includes(seriesName.toLowerCase())
      );

      if (!matchedSeries) {
        const embed = new EmbedBuilder()
          .setTitle('🔍 Series Not Found')
          .setDescription(`No series found matching "${seriesName}". Make sure the series is added to Sonarr.`)
          .setColor(0xff6600)
          .setTimestamp();

        await interaction.editReply({ embeds: [embed] });
        return;
      }

      // Get missing episodes for this series
      const missingEpisodes = await this.sonarrClient.getMissingEpisodes(matchedSeries.id);

      if (missingEpisodes.length === 0) {
        const embed = new EmbedBuilder()
          .setTitle('✅ No Missing Episodes')
          .setDescription(`**${matchedSeries.title}** has no missing episodes!`)
          .setColor(0x00ff00)
          .setTimestamp();

        await interaction.editReply({ embeds: [embed] });
        return;
      }

      // Group episodes by season
      const episodesBySeason = new Map<number, typeof missingEpisodes>();
      missingEpisodes.forEach(episode => {
        if (!episodesBySeason.has(episode.seasonNumber)) {
          episodesBySeason.set(episode.seasonNumber, []);
        }
        episodesBySeason.get(episode.seasonNumber)!.push(episode);
      });

      const embed = new EmbedBuilder()
        .setTitle(`🔍 Missing Episodes: ${matchedSeries.title}`)
        .setColor(0xff6600)
        .setTimestamp();

      let description = `Found ${missingEpisodes.length} missing episode${missingEpisodes.length !== 1 ? 's' : ''}:\n\n`;
      
      let totalShown = 0;
      const maxEpisodes = 15;

      for (const [seasonNum, seasonEpisodes] of episodesBySeason) {
        if (totalShown >= maxEpisodes) break;

        description += `**Season ${seasonNum}**\n`;
        
        for (const episode of seasonEpisodes.slice(0, maxEpisodes - totalShown)) {
          const monitorIcon = episode.monitored ? '📺' : '🔇';
          const airDate = episode.airDateUtc ? 
            new Date(episode.airDateUtc).toLocaleDateString() : 'TBA';
          
          description += `${monitorIcon} S${episode.seasonNumber.toString().padStart(2, '0')}E${episode.episodeNumber.toString().padStart(2, '0')}`;
          
          if (episode.title && episode.title !== 'TBA') {
            description += ` - ${episode.title}`;
          }
          
          description += ` (${airDate})`;
          description += '\n';
          totalShown++;
        }
        description += '\n';
      }

      if (missingEpisodes.length > maxEpisodes) {
        description += `*...and ${missingEpisodes.length - maxEpisodes} more episodes*\n`;
      }

      description += `\n📊 **Series Stats:**\n`;
      description += `• Episodes: ${matchedSeries.episodeFileCount}/${matchedSeries.episodeCount}\n`;
      description += `• Seasons: ${matchedSeries.seasonCount}\n`;
      description += `• Status: ${matchedSeries.status}\n`;
      description += `• Monitored: ${matchedSeries.monitored ? 'Yes' : 'No'}\n`;
      if (matchedSeries.network) {
        description += `• Network: ${matchedSeries.network}\n`;
      }

      embed.setDescription(description);
      embed.setFooter({ text: '📺 Monitored • 🔇 Unmonitored' });

      await interaction.editReply({ embeds: [embed] });

    } catch (error) {
      console.error('Series search command error:', error);
      
      const errorEmbed = new EmbedBuilder()
        .setTitle('🔍 Search Error')
        .setDescription(`Failed to search for missing episodes: ${error instanceof Error ? error.message : 'Unknown error'}`)
        .setColor(0xff0000)
        .setTimestamp();

      await interaction.editReply({ embeds: [errorEmbed] });
    }
  }
}