import { 
  SlashCommandBuilder, 
  ChatInputCommandInteraction, 
  EmbedBuilder,
  ActionRowBuilder,
  StringSelectMenuBuilder,
  StringSelectMenuOptionBuilder,
  ButtonBuilder,
  ButtonStyle,
  ComponentType,
  SlashCommandOptionsOnlyBuilder
} from 'discord.js';
import { QBittorrentClient } from '../services/qbittorrent-client.js';
import { SonarrClient } from '../services/sonarr-client.js';
import { RadarrClient } from '../services/radarr-client.js';
import { BlockedItemDetails } from '../types.js';

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

        // Delete the no-episodes message after 30 seconds
        setTimeout(async () => {
          try {
            await interaction.deleteReply();
          } catch (error) {
            console.error('Failed to delete calendar message:', error);
          }
        }, 30000);
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

        // Group episodes by series
        const episodesBySeries = new Map<string, typeof dayEpisodes>();
        dayEpisodes.forEach(episode => {
          const key = `${episode.seriesTitle}|${episode.network || 'Unknown'}`;
          if (!episodesBySeries.has(key)) {
            episodesBySeries.set(key, []);
          }
          episodesBySeries.get(key)!.push(episode);
        });

        for (const [seriesKey, seriesEpisodes] of episodesBySeries) {
          if (totalShown >= maxEpisodes) break;
          
          const [seriesTitle, network] = seriesKey.split('|');
          const firstEpisode = seriesEpisodes[0];
          const hasFileIcon = seriesEpisodes.every(ep => ep.hasFile) ? '✅' : 
                             seriesEpisodes.some(ep => ep.hasFile) ? '🔄' : '📺';
          const monitorIcon = seriesEpisodes.some(ep => !ep.monitored) ? '🔇' : '';
          const timestamp = firstEpisode.airDateUtc ? 
            `<t:${Math.floor(new Date(firstEpisode.airDateUtc).getTime() / 1000)}:R>` : '';

          if (seriesEpisodes.length === 1) {
            // Single episode - show episode details
            const episode = seriesEpisodes[0];
            description += `${hasFileIcon}${monitorIcon} **${seriesTitle}** S${episode.seasonNumber.toString().padStart(2, '0')}E${episode.episodeNumber.toString().padStart(2, '0')}`;
            if (episode.title && episode.title !== 'TBA') {
              description += ` - ${episode.title}`;
            }
            if (timestamp) {
              description += ` ${timestamp}`;
            }
            if (network !== 'Unknown') {
              description += ` • ${network}`;
            }
            description += '\n';
            totalShown++;
          } else {
            // Multiple episodes - show range
            const sortedEpisodes = seriesEpisodes.sort((a, b) => a.episodeNumber - b.episodeNumber);
            const firstEp = sortedEpisodes[0];
            const lastEp = sortedEpisodes[sortedEpisodes.length - 1];
            
            description += `${hasFileIcon}${monitorIcon} **${seriesTitle}** S${firstEp.seasonNumber.toString().padStart(2, '0')}E${firstEp.episodeNumber.toString().padStart(2, '0')}-E${lastEp.episodeNumber.toString().padStart(2, '0')} (${seriesEpisodes.length} episodes)`;
            if (timestamp) {
              description += ` ${timestamp}`;
            }
            if (network !== 'Unknown') {
              description += ` • ${network}`;
            }
            description += '\n';
            totalShown += seriesEpisodes.length;
          }
        }
      }

      if (episodes.length > maxEpisodes) {
        description += `\n*...and ${episodes.length - maxEpisodes} more episodes*`;
      }

      embed.setDescription(description);
      embed.setFooter({ text: '✅ Downloaded • 🔄 Partially Downloaded • 📺 Airing • 🔇 Unmonitored' });

      await interaction.editReply({ embeds: [embed] });

      // Delete the calendar message after 2 minutes to keep channel clean
      setTimeout(async () => {
        try {
          await interaction.deleteReply();
        } catch (error) {
          console.error('Failed to delete calendar message:', error);
        }
      }, 120000);

    } catch (error) {
      console.error('Calendar command error:', error);
      
      const errorEmbed = new EmbedBuilder()
        .setTitle('📅 Calendar Error')
        .setDescription(`Failed to fetch calendar: ${error instanceof Error ? error.message : 'Unknown error'}`)
        .setColor(0xff0000)
        .setTimestamp();

      await interaction.editReply({ embeds: [errorEmbed] });

      // Delete error message after 15 seconds
      setTimeout(async () => {
        try {
          await interaction.deleteReply();
        } catch (error) {
          console.error('Failed to delete calendar error message:', error);
        }
      }, 15000);
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

  public sonarrClient: SonarrClient;

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

        // Delete the not-found message after 30 seconds
        setTimeout(async () => {
          try {
            await interaction.deleteReply();
          } catch (error) {
            console.error('Failed to delete series-search message:', error);
          }
        }, 30000);
        return;
      }

      // Get detailed series information and missing episodes
      const [detailedSeries, missingEpisodes] = await Promise.all([
        this.sonarrClient.getSeriesById(matchedSeries.id),
        this.sonarrClient.getMissingEpisodes(matchedSeries.id)
      ]);

      // Use detailed series info if available, fallback to basic info
      const seriesInfo = detailedSeries || matchedSeries;

      if (missingEpisodes.length === 0) {
        const embed = new EmbedBuilder()
          .setTitle('✅ No Missing Episodes')
          .setDescription(`**${seriesInfo.title}** has no missing episodes!`)
          .setColor(0x00ff00)
          .setTimestamp();

        await interaction.editReply({ embeds: [embed] });

        // Delete the no-missing-episodes message after 30 seconds
        setTimeout(async () => {
          try {
            await interaction.deleteReply();
          } catch (error) {
            console.error('Failed to delete series-search message:', error);
          }
        }, 30000);
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
        .setTitle(`🔍 Missing Episodes: ${seriesInfo.title}`)
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
      description += `• Episodes: ${seriesInfo.episodeFileCount}/${seriesInfo.episodeCount}\n`;
      description += `• Seasons: ${seriesInfo.seasonCount}\n`;
      description += `• Status: ${seriesInfo.status}\n`;
      description += `• Monitored: ${seriesInfo.monitored ? 'Yes' : 'No'}\n`;
      if (seriesInfo.network) {
        description += `• Network: ${seriesInfo.network}\n`;
      }

      embed.setDescription(description);
      embed.setFooter({ text: '📺 Monitored • 🔇 Unmonitored' });

      // Add button to start search
      const searchButton = new ActionRowBuilder<StringSelectMenuBuilder>()
        .addComponents(
          new StringSelectMenuBuilder()
            .setCustomId(`search_series_${seriesInfo.id}`)
            .setPlaceholder('Start searching for missing episodes?')
            .addOptions(
              new StringSelectMenuOptionBuilder()
                .setLabel('🔍 Start Search')
                .setDescription('Begin searching for all missing episodes')
                .setValue('start_search'),
              new StringSelectMenuOptionBuilder()
                .setLabel('❌ Cancel')
                .setDescription('Just view the missing episodes')
                .setValue('cancel')
            )
        );

      await interaction.editReply({ 
        embeds: [embed],
        components: [searchButton]
      });

      // Delete the search results after 2 minutes to keep channel clean
      setTimeout(async () => {
        try {
          await interaction.deleteReply();
        } catch (error) {
          console.error('Failed to delete series-search message:', error);
        }
      }, 120000);

    } catch (error) {
      console.error('Series search command error:', error);
      
      const errorEmbed = new EmbedBuilder()
        .setTitle('🔍 Search Error')
        .setDescription(`Failed to search for missing episodes: ${error instanceof Error ? error.message : 'Unknown error'}`)
        .setColor(0xff0000)
        .setTimestamp();

      await interaction.editReply({ embeds: [errorEmbed] });

      // Delete error message after 15 seconds
      setTimeout(async () => {
        try {
          await interaction.deleteReply();
        } catch (error) {
          console.error('Failed to delete series-search error message:', error);
        }
      }, 15000);
    }
  }
}

export class UnblockCommand implements SlashCommand {
  data = new SlashCommandBuilder()
    .setName('unblock')
    .setDescription('Process import blocked files with approval/rejection workflow');

  private radarrClient: RadarrClient;
  private sonarrClient: SonarrClient;

  constructor(radarrClient: RadarrClient, sonarrClient: SonarrClient) {
    this.radarrClient = radarrClient;
    this.sonarrClient = sonarrClient;
  }

  async execute(interaction: ChatInputCommandInteraction): Promise<void> {
    await interaction.deferReply();

    try {
      // Get all import blocked items from both services
      const [radarrBlocked, sonarrBlocked] = await Promise.all([
        this.radarrClient.getImportBlockedItems(),
        this.sonarrClient.getImportBlockedItems()
      ]);

      const allBlocked = [
        ...radarrBlocked.map(item => ({ ...item, service: 'radarr' as const })),
        ...sonarrBlocked.map(item => ({ ...item, service: 'sonarr' as const }))
      ];

      if (allBlocked.length === 0) {
        const embed = new EmbedBuilder()
          .setTitle('✅ No Import Blocked Items')
          .setDescription('There are no files currently blocked from import.')
          .setColor(0x00ff00)
          .setTimestamp();

        await interaction.editReply({ embeds: [embed] });

        setTimeout(async () => {
          try {
            await interaction.deleteReply();
          } catch (error) {
            console.error('Failed to delete unblock message:', error);
          }
        }, 30000);
        return;
      }

      // Start the interactive flow
      await this.processBlockedItems(interaction, allBlocked, 0);

    } catch (error) {
      console.error('Unblock command error:', error);
      
      const errorEmbed = new EmbedBuilder()
        .setTitle('🚫 Unblock Error')
        .setDescription(`Failed to fetch import blocked items: ${error instanceof Error ? error.message : 'Unknown error'}`)
        .setColor(0xff0000)
        .setTimestamp();

      await interaction.editReply({ embeds: [errorEmbed] });

      setTimeout(async () => {
        try {
          await interaction.deleteReply();
        } catch (error) {
          console.error('Failed to delete unblock error message:', error);
        }
      }, 15000);
    }
  }

  private async processBlockedItems(
    interaction: ChatInputCommandInteraction, 
    blockedItems: Array<{id: number, title: string, service: 'radarr' | 'sonarr'}>, 
    currentIndex: number,
    processedCount: { approved: number; rejected: number; skipped: number } = { approved: 0, rejected: 0, skipped: 0 }
  ): Promise<void> {
    if (currentIndex >= blockedItems.length) {
      // Show final summary
      const embed = new EmbedBuilder()
        .setTitle('🎉 Unblock Complete')
        .setDescription(`Processed ${blockedItems.length} import blocked items:\n\n` +
          `✅ **Approved**: ${processedCount.approved}\n` +
          `❌ **Rejected**: ${processedCount.rejected}\n` +
          `⏭️ **Skipped**: ${processedCount.skipped}`)
        .setColor(0x00ff00)
        .setTimestamp();

      await interaction.editReply({ embeds: [embed], components: [] });

      setTimeout(async () => {
        try {
          await interaction.deleteReply();
        } catch (error) {
          console.error('Failed to delete unblock summary message:', error);
        }
      }, 60000);
      return;
    }

    const currentItem = blockedItems[currentIndex];
    
    try {
      // Get detailed information about the current item
      const client = currentItem.service === 'radarr' ? this.radarrClient : this.sonarrClient;
      const details = await client.getDetailedBlockedItem(currentItem.id);
      
      // Create detailed embed
      const embed = this.createDetailedEmbed(currentItem, details, currentIndex + 1, blockedItems.length);
      
      // Create action buttons
      const buttons = new ActionRowBuilder<ButtonBuilder>()
        .addComponents(
          new ButtonBuilder()
            .setCustomId(`unblock_approve_${currentItem.service}_${currentItem.id}_${currentIndex}`)
            .setLabel('✅ Approve Import')
            .setStyle(ButtonStyle.Success),
          new ButtonBuilder()
            .setCustomId(`unblock_reject_${currentItem.service}_${currentItem.id}_${currentIndex}`)
            .setLabel('❌ Reject & Delete')
            .setStyle(ButtonStyle.Danger),
          new ButtonBuilder()
            .setCustomId(`unblock_skip_${currentItem.service}_${currentItem.id}_${currentIndex}`)
            .setLabel('⏭️ Skip')
            .setStyle(ButtonStyle.Secondary)
        );

      await interaction.editReply({ 
        embeds: [embed], 
        components: [buttons] 
      });

    } catch (error) {
      console.error(`Error processing blocked item ${currentItem.id}:`, error);
      
      // Skip this item and continue
      await this.processBlockedItems(interaction, blockedItems, currentIndex + 1, {
        ...processedCount,
        skipped: processedCount.skipped + 1
      });
    }
  }

  private createDetailedEmbed(
    item: {id: number, title: string, service: 'radarr' | 'sonarr'}, 
    details: any,
    current: number,
    total: number
  ): EmbedBuilder {
    const embed = new EmbedBuilder()
      .setTitle(`🚫 Import Blocked (${current}/${total})`)
      .setColor(0xff6600)
      .setTimestamp();

    // Extract key information
    const size = details.size ? `${(details.size / 1073741824).toFixed(1)}GB` : 'Unknown';
    const quality = details.quality?.quality?.name || 'Unknown';
    const downloadClient = details.downloadClient || 'Unknown';
    const indexer = details.indexer || 'Unknown';
    const protocol = details.protocol || 'Unknown';
    
    // Get blocking reason from status messages
    let blockingReason = 'Unknown reason';
    if (details.statusMessages && details.statusMessages.length > 0) {
      const messages = details.statusMessages[0]?.messages || [];
      if (messages.length > 0) {
        blockingReason = messages.join('; ');
      }
    }

    const addedDate = details.added ? new Date(details.added).toLocaleString() : 'Unknown';
    const outputPath = details.outputPath || 'Unknown';

    let description = `**${item.title}**\n\n`;
    description += `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`;
    description += `📂 **File Path**: \`${outputPath}\`\n`;
    description += `📊 **Size**: ${size}\n`;
    description += `🎬 **Quality**: ${quality}\n`;
    description += `📡 **Source**: ${indexer} (${protocol})\n`;
    description += `💾 **Client**: ${downloadClient}\n`;
    description += `⏰ **Added**: ${addedDate}\n\n`;
    description += `❌ **Blocking Reason**:\n`;
    description += `*${blockingReason}*\n\n`;
    description += `Choose an action to continue:`;

    embed.setDescription(description);
    
    return embed;
  }

  // Method to handle button interactions (will be called from bot.ts)
  async handleButtonInteraction(
    interaction: any, 
    action: string, 
    service: 'radarr' | 'sonarr', 
    itemId: number, 
    currentIndex: number,
    allBlocked: Array<{id: number, title: string, service: 'radarr' | 'sonarr'}>,
    processedCount: { approved: number; rejected: number; skipped: number }
  ): Promise<void> {
    await interaction.deferUpdate();

    const client = service === 'radarr' ? this.radarrClient : this.sonarrClient;
    const currentItem = allBlocked.find(item => item.id === itemId);

    try {
      let resultMessage = '';
      let newProcessedCount = { ...processedCount };

      switch (action) {
        case 'approve':
          try {
            await client.approveImport(itemId);
            resultMessage = `✅ **Approved**: ${currentItem?.title}`;
            newProcessedCount.approved++;
          } catch (error) {
            resultMessage = `❌ **Approval Failed**: ${currentItem?.title} - ${error instanceof Error ? error.message : 'Unknown error'}`;
            newProcessedCount.skipped++;
          }
          break;

        case 'reject':
          try {
            await client.removeQueueItems([itemId]);
            resultMessage = `❌ **Rejected**: ${currentItem?.title}`;
            newProcessedCount.rejected++;
          } catch (error) {
            resultMessage = `❌ **Rejection Failed**: ${currentItem?.title} - ${error instanceof Error ? error.message : 'Unknown error'}`;
            newProcessedCount.skipped++;
          }
          break;

        case 'skip':
          resultMessage = `⏭️ **Skipped**: ${currentItem?.title}`;
          newProcessedCount.skipped++;
          break;
      }

      // Show brief result message
      const resultEmbed = new EmbedBuilder()
        .setTitle('Processing...')
        .setDescription(resultMessage)
        .setColor(action === 'approve' ? 0x00ff00 : action === 'reject' ? 0xff0000 : 0x666666)
        .setTimestamp();

      await interaction.editReply({ embeds: [resultEmbed], components: [] });

      // Wait briefly to show the result, then continue
      setTimeout(async () => {
        await this.processBlockedItems(interaction, allBlocked, currentIndex + 1, newProcessedCount);
      }, 1500);

    } catch (error) {
      console.error(`Error handling ${action} for item ${itemId}:`, error);
      
      // Skip this item and continue
      await this.processBlockedItems(interaction, allBlocked, currentIndex + 1, {
        ...processedCount,
        skipped: processedCount.skipped + 1
      });
    }
  }
}