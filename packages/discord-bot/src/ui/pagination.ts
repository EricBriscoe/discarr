import { ActionRowBuilder, ButtonBuilder, ButtonStyle, EmbedBuilder } from 'discord.js';
import { AnyDownloadItem } from '@discarr/core';

export interface PaginationOptions { itemsPerPage: number; maxFields: number; }

export class PaginationManager {
  private currentPage = 1;
  private totalPages = 1;
  private options: PaginationOptions;

  constructor(options: Partial<PaginationOptions> = {}) {
    this.options = { itemsPerPage: 6, maxFields: 5, ...options } as PaginationOptions;
  }

  createPaginatedEmbed(items: AnyDownloadItem[], total: number): { embed: EmbedBuilder; components: ActionRowBuilder<ButtonBuilder>[] } {
    this.totalPages = Math.max(1, Math.ceil(items.length / this.options.itemsPerPage));
    if (this.currentPage > this.totalPages) this.currentPage = this.totalPages;
    const startIndex = (this.currentPage - 1) * this.options.itemsPerPage;
    const pageItems = items.slice(startIndex, startIndex + this.options.itemsPerPage);
    const embed = this.createDownloadsEmbed(pageItems, total);
    if (this.totalPages > 1) embed.setFooter({ text: `Page ${this.currentPage} of ${this.totalPages} • Showing ${pageItems.length} of ${total} downloads` });
    const components = this.totalPages > 1 ? [this.createPaginationButtons()] : [];
    return { embed, components };
  }

  private createDownloadsEmbed(items: AnyDownloadItem[], total: number): EmbedBuilder {
    const lastUpdate = `<t:${Math.floor(Date.now() / 1000)}:R>`;
    const embed = new EmbedBuilder().setTitle('📥 Active Downloads').setDescription(`Last updated: ${lastUpdate}`).setTimestamp().setColor(0x00ff00);
    if (total === 0) { embed.setDescription(`Last updated: ${lastUpdate}\n\nNo active downloads`).setColor(0x808080); return embed; }
    if (items.length > 0) {
      const downloadsList = items.map(item => {
        const progressBar = this.createProgressBar(item.progress);
        const timeLeft = item.timeLeft || '∞';
        const size = item.size ? ` • ${item.size.toFixed(1)}GB` : '';
        const emoji = item.service === 'radarr' ? '🎬' : '📺';
        return `${emoji} **${this.truncateTitle(item.title)}**\n${progressBar} ${item.progress.toFixed(1)}%${size} • ${timeLeft}\n*Status: ${item.status || 'unknown'}*`;
      }).join('\n\n');
      embed.addFields({ name: `Downloads (${items.length} on this page)`, value: downloadsList, inline: false });
    }
    return embed;
  }

  private createPaginationButtons(): ActionRowBuilder<ButtonBuilder> {
    const row = new ActionRowBuilder<ButtonBuilder>();
    row.addComponents(new ButtonBuilder().setCustomId('pagination_first').setLabel('⏮️').setStyle(ButtonStyle.Secondary).setDisabled(this.currentPage === 1));
    row.addComponents(new ButtonBuilder().setCustomId('pagination_prev').setLabel('◀️').setStyle(ButtonStyle.Primary).setDisabled(this.currentPage === 1));
    row.addComponents(new ButtonBuilder().setCustomId('pagination_info').setLabel(`${this.currentPage}/${this.totalPages}`).setStyle(ButtonStyle.Secondary).setDisabled(true));
    row.addComponents(new ButtonBuilder().setCustomId('pagination_next').setLabel('▶️').setStyle(ButtonStyle.Primary).setDisabled(this.currentPage === this.totalPages));
    row.addComponents(new ButtonBuilder().setCustomId('pagination_last').setLabel('⏭️').setStyle(ButtonStyle.Secondary).setDisabled(this.currentPage === this.totalPages));
    return row;
  }

  handleButton(buttonId: string): boolean {
    const oldPage = this.currentPage;
    switch (buttonId) {
      case 'pagination_first': this.currentPage = 1; break;
      case 'pagination_prev': this.currentPage = Math.max(1, this.currentPage - 1); break;
      case 'pagination_next': this.currentPage = Math.min(this.totalPages, this.currentPage + 1); break;
      case 'pagination_last': this.currentPage = this.totalPages; break;
      default: return false;
    }
    return oldPage !== this.currentPage;
  }

  private createProgressBar(progress: number, length = 10): string { const filled = Math.round((progress / 100) * length); const empty = length - filled; return '█'.repeat(filled) + '░'.repeat(empty); }
  private truncateTitle(title: string, maxLength = 45): string { return title.length > maxLength ? `${title.substring(0, maxLength - 3)}...` : title; }
}

