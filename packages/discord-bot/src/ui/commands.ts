import { SlashCommandBuilder, ChatInputCommandInteraction, EmbedBuilder, ActionRowBuilder, StringSelectMenuBuilder, StringSelectMenuOptionBuilder, SlashCommandOptionsOnlyBuilder } from 'discord.js';
import { QBittorrentClient, SonarrClient, RadarrClient, BlockedItemDetails } from '@discarr/core';

export interface SlashCommand { data: SlashCommandBuilder | SlashCommandOptionsOnlyBuilder; execute: (interaction: ChatInputCommandInteraction) => Promise<void>; }

export class CleanupCommand implements SlashCommand {
  data = new SlashCommandBuilder().setName('cleanup').setDescription('Remove seeding/stalled/stuck torrents with sonarr/radarr labels from qBittorrent');
  constructor(private qbittorrentClient: QBittorrentClient) {}
  async execute(interaction: ChatInputCommandInteraction): Promise<void> {
    await interaction.deferReply();
    try {
      const embed = new EmbedBuilder().setTitle('🧹 Cleanup in Progress').setDescription('Scanning qBittorrent for seeding/stalled/stuck torrents with sonarr/radarr labels...').setColor(0xffaa00).setTimestamp();
      await interaction.editReply({ embeds: [embed] });
      const torrentsToRemove = await this.qbittorrentClient.getSeedinOrStalledTorrentsWithLabels();
      if (torrentsToRemove.length === 0) {
        embed.setTitle('🧹 Cleanup Complete').setDescription('No seeding/stalled/stuck torrents with sonarr/radarr labels found.').setColor(0x00ff00);
        await interaction.editReply({ embeds: [embed] });
        setTimeout(async () => { try { await interaction.deleteReply(); } catch {} }, 3000);
        return;
      }
      let updateDescription = `Found ${torrentsToRemove.length} torrent${torrentsToRemove.length !== 1 ? 's' : ''} to clean up:\n`;
      updateDescription += torrentsToRemove.slice(0, 5).map(t => `• ${t.name} (${t.category}/${t.state})`).join('\n');
      if (torrentsToRemove.length > 5) updateDescription += `\n• ...and ${torrentsToRemove.length - 5} more`;
      updateDescription += `\n\nRemoving from qBittorrent and disk...`;
      embed.setDescription(updateDescription).setColor(0xff6600);
      await interaction.editReply({ embeds: [embed] });
      const results = await this.qbittorrentClient.deleteTorrents(torrentsToRemove.map(t => t.hash), true);
      const successful = results.filter(r => r.success).length; const failed = results.length - successful;
      const resultEmbed = new EmbedBuilder().setTitle('🧹 Cleanup Complete').setTimestamp().setColor(failed === 0 ? 0x00ff00 : 0xff6600);
      let resultDescription = '';
      if (successful > 0) resultDescription += `✅ Removed ${successful} torrent${successful !== 1 ? 's' : ''} from qBittorrent and disk\n`;
      if (failed > 0) resultDescription += `❌ Failed to remove ${failed} torrent${failed !== 1 ? 's' : ''}\n`;
      resultEmbed.setDescription(resultDescription.trim());
      await interaction.editReply({ embeds: [resultEmbed] });
      setTimeout(async () => { try { await interaction.deleteReply(); } catch {} }, 5000);
    } catch (error) {
      const errorEmbed = new EmbedBuilder().setTitle('🧹 Cleanup Failed').setDescription(`An error occurred during cleanup: ${error instanceof Error ? error.message : 'Unknown error'}`).setColor(0xff0000).setTimestamp();
      await interaction.editReply({ embeds: [errorEmbed] });
      setTimeout(async () => { try { await interaction.deleteReply(); } catch {} }, 10000);
    }
  }
}

export class CalendarCommand implements SlashCommand {
  data = new SlashCommandBuilder().setName('calendar').setDescription('Show upcoming TV episodes for the next week').addIntegerOption(option => option.setName('days').setDescription('Number of days to look ahead (1-14)').setMinValue(1).setMaxValue(14).setRequired(false));
  constructor(public sonarrClient: SonarrClient) {}
  async execute(interaction: ChatInputCommandInteraction): Promise<void> {
    await interaction.deferReply();
    try {
      const days = (interaction.options.get('days')?.value as number) || 7;
      const episodes = await this.sonarrClient.getCalendarEpisodes(days);
      if (episodes.length === 0) {
        const embed = new EmbedBuilder().setTitle('📅 No Upcoming Episodes').setDescription(`No episodes scheduled for the next ${days} day${days !== 1 ? 's' : ''}.`).setColor(0x666666).setTimestamp();
        await interaction.editReply({ embeds: [embed] });
        setTimeout(async () => { try { await interaction.deleteReply(); } catch {} }, 30000);
        return;
      }
      const episodesByDate = new Map<string, typeof episodes>();
      episodes.forEach(ep => { if (ep.airDateUtc) { const date = new Date(ep.airDateUtc).toDateString(); if (!episodesByDate.has(date)) episodesByDate.set(date, []); episodesByDate.get(date)!.push(ep); } });
      const embed = new EmbedBuilder().setTitle(`📅 Upcoming Episodes (Next ${days} Days)`).setColor(0x0099ff).setTimestamp();
      let description = '';
      let totalShown = 0; const maxEpisodes = 20;
      for (const [date, dayEpisodes] of episodesByDate) {
        if (totalShown >= maxEpisodes) break;
        const dateObj = new Date(date);
        const isToday = dateObj.toDateString() === new Date().toDateString();
        const isTomorrow = dateObj.toDateString() === new Date(Date.now() + 86400000).toDateString();
        let dateLabel = date; if (isToday) dateLabel = '**Today**'; else if (isTomorrow) dateLabel = '**Tomorrow**';
        description += `\n**${dateLabel}**\n`;
        const episodesBySeries = new Map<string, typeof dayEpisodes>();
        dayEpisodes.forEach(episode => { const key = `${episode.seriesTitle}|${episode.network || 'Unknown'}`; if (!episodesBySeries.has(key)) episodesBySeries.set(key, []); episodesBySeries.get(key)!.push(episode); });
        for (const [seriesKey, seriesEpisodes] of episodesBySeries) {
          if (totalShown >= maxEpisodes) break;
          const [seriesTitle, network] = seriesKey.split('|');
          const firstEpisode = seriesEpisodes[0];
          const hasFileIcon = seriesEpisodes.every(ep => ep.hasFile) ? '✅' : seriesEpisodes.some(ep => ep.hasFile) ? '🔄' : '📺';
          const monitorIcon = seriesEpisodes.some(ep => !ep.monitored) ? '🔇' : '';
          const timestamp = firstEpisode.airDateUtc ? `<t:${Math.floor(new Date(firstEpisode.airDateUtc).getTime() / 1000)}:R>` : '';
          if (seriesEpisodes.length === 1) {
            const episode = seriesEpisodes[0];
            description += `${hasFileIcon}${monitorIcon} **${seriesTitle}** S${episode.seasonNumber.toString().padStart(2, '0')}E${episode.episodeNumber.toString().padStart(2, '0')}`;
            if (episode.title && episode.title !== 'TBA') description += ` - ${episode.title}`;
            if (timestamp) description += ` ${timestamp}`; if (network !== 'Unknown') description += ` • ${network}`; description += '\n'; totalShown++;
          } else {
            description += `${hasFileIcon}${monitorIcon} **${seriesTitle}** (${seriesEpisodes.length} episodes)`;
            if (timestamp) description += ` starting ${timestamp}`;
            if (network !== 'Unknown') description += ` • ${network}`;
            description += '\n'; totalShown++;
          }
        }
      }
      embed.setDescription(description);
      embed.setFooter({ text: '✅ Downloaded • 🔄 Partially Downloaded • 📺 Airing • 🔇 Unmonitored' });
      await interaction.editReply({ embeds: [embed] });
      setTimeout(async () => { try { await interaction.deleteReply(); } catch {} }, 120000);
    } catch (error) {
      const errorEmbed = new EmbedBuilder().setTitle('📅 Calendar Error').setDescription(`Failed to fetch calendar: ${error instanceof Error ? error.message : 'Unknown error'}`).setColor(0xff0000).setTimestamp();
      await interaction.editReply({ embeds: [errorEmbed] });
      setTimeout(async () => { try { await interaction.deleteReply(); } catch {} }, 15000);
    }
  }
}

export class SeriesSearchCommand implements SlashCommand {
  data = new SlashCommandBuilder().setName('series-search').setDescription('Search for missing episodes for a specific series').addStringOption(option => option.setName('series').setDescription('Series name to search for missing episodes').setRequired(true).setAutocomplete(true));
  constructor(public sonarrClient: SonarrClient) {}
  async execute(interaction: ChatInputCommandInteraction): Promise<void> {
    await interaction.deferReply();
    try {
      const seriesName = interaction.options.get('series')?.value as string;
      const allSeries = await this.sonarrClient.getSeriesList();
      const matchedSeries = allSeries.find(s => s.title.toLowerCase().includes(seriesName.toLowerCase()));
      if (!matchedSeries) {
        const embed = new EmbedBuilder().setTitle('🔍 Series Not Found').setDescription(`No series found matching "${seriesName}". Make sure the series is added to Sonarr.`).setColor(0xff6600).setTimestamp();
        await interaction.editReply({ embeds: [embed] });
        setTimeout(async () => { try { await interaction.deleteReply(); } catch {} }, 30000);
        return;
      }
      const [detailedSeries, missingEpisodes] = await Promise.all([
        this.sonarrClient.getSeriesById(matchedSeries.id),
        this.sonarrClient.getMissingEpisodes(matchedSeries.id)
      ]);
      const seriesInfo = detailedSeries || matchedSeries;
      if (missingEpisodes.length === 0) {
        const embed = new EmbedBuilder().setTitle('✅ No Missing Episodes').setDescription(`**${seriesInfo.title}** has no missing episodes!`).setColor(0x00ff00).setTimestamp();
        await interaction.editReply({ embeds: [embed] });
        setTimeout(async () => { try { await interaction.deleteReply(); } catch {} }, 30000);
        return;
      }
      const episodesBySeason = new Map<number, typeof missingEpisodes>();
      missingEpisodes.forEach(episode => { if (!episodesBySeason.has(episode.seasonNumber)) episodesBySeason.set(episode.seasonNumber, []); episodesBySeason.get(episode.seasonNumber)!.push(episode); });
      const embed = new EmbedBuilder().setTitle(`🔍 Missing Episodes: ${seriesInfo.title}`).setColor(0xff6600).setTimestamp();
      let description = `Found ${missingEpisodes.length} missing episode${missingEpisodes.length !== 1 ? 's' : ''}:\n\n`;
      let totalShown = 0; const maxEpisodes = 15;
      for (const [seasonNum, seasonEpisodes] of episodesBySeason) {
        if (totalShown >= maxEpisodes) break;
        description += `**Season ${seasonNum}**\n`;
        for (const episode of seasonEpisodes.slice(0, maxEpisodes - totalShown)) {
          const monitorIcon = episode.monitored ? '📺' : '🔇';
          const airDate = episode.airDateUtc ? new Date(episode.airDateUtc).toLocaleDateString() : 'TBA';
          description += `${monitorIcon} S${episode.seasonNumber.toString().padStart(2, '0')}E${episode.episodeNumber.toString().padStart(2, '0')}`;
          if (episode.title && episode.title !== 'TBA') description += ` - ${episode.title}`;
          description += ` (${airDate})\n`;
          totalShown++;
        }
        description += '\n';
      }
      if (missingEpisodes.length > maxEpisodes) description += `*...and ${missingEpisodes.length - maxEpisodes} more episodes*\n`;
      description += `\n📊 **Series Stats:**\n`;
      description += `• Episodes: ${seriesInfo.episodeFileCount}/${seriesInfo.episodeCount}\n`;
      description += `• Seasons: ${seriesInfo.seasonCount}\n`;
      description += `• Status: ${seriesInfo.status}\n`;
      description += `• Monitored: ${seriesInfo.monitored ? 'Yes' : 'No'}\n`;
      if (seriesInfo.network) description += `• Network: ${seriesInfo.network}\n`;
      embed.setDescription(description); embed.setFooter({ text: '📺 Monitored • 🔇 Unmonitored' });
      const searchButton = new ActionRowBuilder<StringSelectMenuBuilder>().addComponents(
        new StringSelectMenuBuilder().setCustomId(`search_series_${seriesInfo.id}`).setPlaceholder('Start searching for missing episodes?').addOptions(
          new StringSelectMenuOptionBuilder().setLabel('🔍 Start Search').setDescription('Begin searching for all missing episodes').setValue('start_search'),
          new StringSelectMenuOptionBuilder().setLabel('❌ Cancel').setDescription('Just view the missing episodes').setValue('cancel')
        )
      );
      await interaction.editReply({ embeds: [embed], components: [searchButton] });
      setTimeout(async () => { try { await interaction.deleteReply(); } catch {} }, 120000);
    } catch (error) {
      const errorEmbed = new EmbedBuilder().setTitle('🔍 Search Error').setDescription(`Failed to search for missing episodes: ${error instanceof Error ? error.message : 'Unknown error'}`).setColor(0xff0000).setTimestamp();
      await interaction.editReply({ embeds: [errorEmbed] });
      setTimeout(async () => { try { await interaction.deleteReply(); } catch {} }, 15000);
    }
  }
}

export class UnblockCommand implements SlashCommand {
  data = new SlashCommandBuilder().setName('unblock').setDescription('Process import blocked files with approval/rejection workflow');
  constructor(private radarrClient: RadarrClient, private sonarrClient: SonarrClient) {}
  async execute(interaction: ChatInputCommandInteraction): Promise<void> {
    await interaction.deferReply();
    try {
      const [radarrBlocked, sonarrBlocked] = await Promise.all([
        this.radarrClient.getImportBlockedItems(),
        this.sonarrClient.getImportBlockedItems()
      ]);
      const allBlocked = [
        ...radarrBlocked.map(item => ({ ...item, service: 'radarr' as const })),
        ...sonarrBlocked.map(item => ({ ...item, service: 'sonarr' as const }))
      ];
      if (allBlocked.length === 0) {
        const embed = new EmbedBuilder().setTitle('✅ No Import Blocked Items').setDescription('Nothing to process.').setColor(0x00ff00).setTimestamp();
        await interaction.editReply({ embeds: [embed] });
        setTimeout(async () => { try { await interaction.deleteReply(); } catch {} }, 5000);
        return;
      }
      const firstItem = allBlocked[0];
      const details = await this.getBlockedItemDetails(firstItem.service, firstItem.id);
      const embed = this.buildBlockedItemEmbed(details);
      const components = this.buildActionButtons(firstItem.service, firstItem.id, 0);
      await interaction.editReply({ embeds: [embed], components });
    } catch (error) {
      const errorEmbed = new EmbedBuilder().setTitle('❌ Unblock Failed').setDescription(`Failed to fetch import blocked items: ${error instanceof Error ? error.message : 'Unknown error'}`).setColor(0xff0000).setTimestamp();
      await interaction.editReply({ embeds: [errorEmbed] });
      setTimeout(async () => { try { await interaction.deleteReply(); } catch {} }, 15000);
    }
  }

  private async getBlockedItemDetails(service: 'radarr' | 'sonarr', id: number): Promise<BlockedItemDetails> {
    const client = service === 'radarr' ? this.radarrClient : this.sonarrClient;
    const item = await (client as any).getDetailedBlockedItem(id);
    const outputPath = item.outputPath || item.path || 'Unknown';
    const title = service === 'radarr' ? (item.title || item.movie?.title || 'Unknown Movie') : `${item.series?.title} - S${item.episode?.seasonNumber?.toString().padStart(2, '0')}E${item.episode?.episodeNumber?.toString().padStart(2, '0')}`;
    const downloadClient = item.downloadClient || 'Unknown';
    const indexer = item.indexer || 'Unknown';
    const protocol = item.protocol || 'Unknown';
    const size = item.size || 0;
    const quality = item.quality || {};
    const languages = item.languages || [];
    const statusMessages = item.statusMessages || [];
    const added = item.added || new Date().toISOString();
    return { id, title, service, downloadClient, indexer, protocol, size, outputPath, quality, languages, statusMessages, added } as BlockedItemDetails;
  }

  private buildActionButtons(service: 'radarr' | 'sonarr', itemId: number, currentIndex: number) {
    const row = new ActionRowBuilder<any>();
    return [row
      .addComponents(
        new (require('discord.js').ButtonBuilder)().setCustomId(`unblock_approve_${service}_${itemId}_${currentIndex}`).setLabel('Approve').setStyle((require('discord.js').ButtonStyle).Success),
        new (require('discord.js').ButtonBuilder)().setCustomId(`unblock_reject_${service}_${itemId}_${currentIndex}`).setLabel('Reject').setStyle((require('discord.js').ButtonStyle).Danger),
        new (require('discord.js').ButtonBuilder)().setCustomId(`unblock_skip_${service}_${itemId}_${currentIndex}`).setLabel('Skip').setStyle((require('discord.js').ButtonStyle).Secondary)
      )
    ];
  }

  private buildBlockedItemEmbed(item: BlockedItemDetails): EmbedBuilder {
    const size = (item.size / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
    const indexer = item.indexer || 'Unknown';
    const protocol = item.protocol || 'Unknown';
    const downloadClient = item.downloadClient || 'Unknown';
    const addedDate = item.added ? new Date(item.added).toLocaleString() : 'Unknown';
    const blockingReason = item.statusMessages?.map(s => `• ${s.title}: ${s.messages.join('; ')}`).join('\n') || 'Unknown reason';
    const outputPath = item.outputPath || 'Unknown';
    const embed = new EmbedBuilder().setTitle('🚫 Import Blocked Item').setColor(0xff0000).setTimestamp();
    let description = `**${item.title}**\n\n`;
    description += `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`;
    description += `📂 **File Path**: \`${outputPath}\`\n`;
    description += `📊 **Size**: ${size}\n`;
    description += `🎬 **Quality**: ${JSON.stringify(item.quality)}\n`;
    description += `📡 **Source**: ${indexer} (${protocol})\n`;
    description += `💾 **Client**: ${downloadClient}\n`;
    description += `⏰ **Added**: ${addedDate}\n\n`;
    description += `❌ **Blocking Reason**:\n*${blockingReason}*\n\n`;
    description += `Choose an action to continue:`;
    embed.setDescription(description);
    return embed;
  }

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
          try { await (client as any).approveImport(itemId); resultMessage = `✅ **Approved**: ${currentItem?.title}`; newProcessedCount.approved++; } 
          catch (error) { resultMessage = `❌ **Approval Failed**: ${currentItem?.title} - ${error instanceof Error ? error.message : 'Unknown error'}`; newProcessedCount.skipped++; }
          break;
        case 'reject':
          try { await (client as any).removeQueueItems([itemId]); resultMessage = `❌ **Rejected**: ${currentItem?.title}`; newProcessedCount.rejected++; } 
          catch (error) { resultMessage = `❌ **Rejection Failed**: ${currentItem?.title} - ${error instanceof Error ? error.message : 'Unknown error'}`; newProcessedCount.skipped++; }
          break;
        case 'skip':
          resultMessage = `⏭️ **Skipped**: ${currentItem?.title}`; newProcessedCount.skipped++; break;
      }
      const resultEmbed = new EmbedBuilder().setTitle('Processing...').setDescription(resultMessage).setColor(action === 'approve' ? 0x00ff00 : action === 'reject' ? 0xff0000 : 0x666666).setTimestamp();
      await interaction.editReply({ embeds: [resultEmbed], components: [] });
      setTimeout(async () => { await this.processBlockedItems(interaction, allBlocked, currentIndex + 1, newProcessedCount); }, 1500);
    } catch (error) {
      await this.processBlockedItems(interaction, allBlocked, currentIndex + 1, { ...processedCount, skipped: processedCount.skipped + 1 });
    }
  }

  private async processBlockedItems(
    interaction: any,
    allBlocked: Array<{ id: number; title: string; service: 'radarr' | 'sonarr' }>,
    index: number,
    processedCount: { approved: number; rejected: number; skipped: number }
  ) {
    if (index >= allBlocked.length) {
      const resultEmbed = new EmbedBuilder().setTitle('✅ Unblock Complete').setDescription(`Approved: ${processedCount.approved} • Rejected: ${processedCount.rejected} • Skipped: ${processedCount.skipped}`).setColor(0x00ff00).setTimestamp();
      await interaction.editReply({ embeds: [resultEmbed], components: [] });
      setTimeout(async () => { try { await interaction.deleteReply(); } catch {} }, 8000);
      return;
    }
    const item = allBlocked[index];
    const details = await this.getBlockedItemDetails(item.service, item.id);
    const embed = this.buildBlockedItemEmbed(details);
    const components = this.buildActionButtons(item.service, item.id, index);
    await interaction.editReply({ embeds: [embed], components });
  }
}
