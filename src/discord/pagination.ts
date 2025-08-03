import { ActionRowBuilder, ButtonBuilder, ButtonStyle, EmbedBuilder } from 'discord.js';
import { MovieDownloadItem, TVDownloadItem } from '../types';
import { DiscordEmbedBuilder } from './embed-builder';

export interface PaginationOptions {
  itemsPerPage: number;
  maxFields: number;
}

export class PaginationManager {
  private currentPage = 1;
  private totalPages = 1;
  private options: PaginationOptions;

  constructor(options: Partial<PaginationOptions> = {}) {
    this.options = {
      itemsPerPage: 6,
      maxFields: 5,
      ...options
    };
  }

  createPaginatedEmbed(
    movies: MovieDownloadItem[],
    tv: TVDownloadItem[],
    total: number
  ): { embed: EmbedBuilder; components: ActionRowBuilder<ButtonBuilder>[] } {
    // Calculate pagination - preserve the order from DownloadMonitor (already sorted by time left)
    const allItems = [...movies, ...tv];
    this.totalPages = Math.max(1, Math.ceil(allItems.length / this.options.itemsPerPage));
    
    // Ensure current page is valid
    if (this.currentPage > this.totalPages) {
      this.currentPage = this.totalPages;
    }

    // Get items for current page
    const startIndex = (this.currentPage - 1) * this.options.itemsPerPage;
    const endIndex = startIndex + this.options.itemsPerPage;
    const pageItems = allItems.slice(startIndex, endIndex);

    // Separate movies and TV for this page
    const pageMovies = pageItems.filter(item => item.service === 'radarr') as MovieDownloadItem[];
    const pageTv = pageItems.filter(item => item.service === 'sonarr') as TVDownloadItem[];

    // Create embed
    const embed = this.createDownloadsEmbed(pageMovies, pageTv, total);
    
    // Add pagination footer
    if (this.totalPages > 1) {
      const footerText = `Page ${this.currentPage} of ${this.totalPages} • Showing ${pageItems.length} of ${total} downloads`;
      embed.setFooter({ text: footerText });
    }

    // Create pagination buttons
    const components = this.totalPages > 1 ? [this.createPaginationButtons()] : [];

    return { embed, components };
  }

  private createDownloadsEmbed(
    movies: MovieDownloadItem[],
    tv: TVDownloadItem[],
    total: number
  ): EmbedBuilder {
    const lastUpdate = `<t:${Math.floor(Date.now() / 1000)}:R>`;
    const embed = new EmbedBuilder()
      .setTitle('📥 Active Downloads')
      .setDescription(`Last updated: ${lastUpdate}`)
      .setTimestamp()
      .setColor(0x00ff00);

    if (total === 0) {
      embed.setDescription(`Last updated: ${lastUpdate}\n\nNo active downloads`);
      embed.setColor(0x808080);
      return embed;
    }

    // Add movies section
    if (movies.length > 0) {
      const movieList = movies.map(movie => {
        const progressBar = this.createProgressBar(movie.progress);
        const timeLeft = movie.timeLeft || '∞';
        const status = movie.status || 'unknown';
        const size = movie.size ? ` • ${movie.size.toFixed(1)}GB` : '';
        return `**${this.truncateTitle(movie.title)}**\n${progressBar} ${movie.progress.toFixed(1)}%${size} • ${timeLeft}\n*Status: ${status}*`;
      }).join('\n\n');

      embed.addFields({
        name: `🎬 Movies (${movies.length} on this page)`,
        value: movieList,
        inline: false,
      });
    }

    // Add TV section
    if (tv.length > 0) {
      const tvList = tv.map(show => {
        const progressBar = this.createProgressBar(show.progress);
        const timeLeft = show.timeLeft || '∞';
        const status = show.status || 'unknown';
        const size = show.size ? ` • ${show.size.toFixed(1)}GB` : '';
        return `**${this.truncateTitle(show.title)}**\n${progressBar} ${show.progress.toFixed(1)}%${size} • ${timeLeft}\n*Status: ${status}*`;
      }).join('\n\n');

      embed.addFields({
        name: `📺 TV Shows (${tv.length} on this page)`,
        value: tvList,
        inline: false,
      });
    }

    return embed;
  }

  private createPaginationButtons(): ActionRowBuilder<ButtonBuilder> {
    const row = new ActionRowBuilder<ButtonBuilder>();

    // First page button
    row.addComponents(
      new ButtonBuilder()
        .setCustomId('pagination_first')
        .setLabel('⏮️')
        .setStyle(ButtonStyle.Secondary)
        .setDisabled(this.currentPage === 1)
    );

    // Previous page button
    row.addComponents(
      new ButtonBuilder()
        .setCustomId('pagination_prev')
        .setLabel('◀️')
        .setStyle(ButtonStyle.Primary)
        .setDisabled(this.currentPage === 1)
    );

    // Page indicator
    row.addComponents(
      new ButtonBuilder()
        .setCustomId('pagination_info')
        .setLabel(`${this.currentPage}/${this.totalPages}`)
        .setStyle(ButtonStyle.Secondary)
        .setDisabled(true)
    );

    // Next page button
    row.addComponents(
      new ButtonBuilder()
        .setCustomId('pagination_next')
        .setLabel('▶️')
        .setStyle(ButtonStyle.Primary)
        .setDisabled(this.currentPage === this.totalPages)
    );

    // Last page button
    row.addComponents(
      new ButtonBuilder()
        .setCustomId('pagination_last')
        .setLabel('⏭️')
        .setStyle(ButtonStyle.Secondary)
        .setDisabled(this.currentPage === this.totalPages)
    );

    return row;
  }

  handleButton(buttonId: string): boolean {
    const oldPage = this.currentPage;

    switch (buttonId) {
      case 'pagination_first':
        this.currentPage = 1;
        break;
      case 'pagination_prev':
        this.currentPage = Math.max(1, this.currentPage - 1);
        break;
      case 'pagination_next':
        this.currentPage = Math.min(this.totalPages, this.currentPage + 1);
        break;
      case 'pagination_last':
        this.currentPage = this.totalPages;
        break;
      default:
        return false;
    }

    return oldPage !== this.currentPage;
  }


  private createProgressBar(progress: number, length = 10): string {
    const filled = Math.round((progress / 100) * length);
    const empty = length - filled;
    return '█'.repeat(filled) + '░'.repeat(empty);
  }

  private truncateTitle(title: string, maxLength = 45): string {
    return title.length > maxLength ? `${title.substring(0, maxLength - 3)}...` : title;
  }

  getCurrentPage(): number {
    return this.currentPage;
  }

  getTotalPages(): number {
    return this.totalPages;
  }
}