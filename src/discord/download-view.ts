import { ActionRowBuilder, ButtonBuilder, ButtonInteraction, EmbedBuilder } from 'discord.js';
import { PaginationManager } from './pagination';
import { MovieDownloadItem, TVDownloadItem } from '../types';

export class DownloadView {
  private paginationManager: PaginationManager;
  private movies: MovieDownloadItem[] = [];
  private tv: TVDownloadItem[] = [];
  private total = 0;

  constructor() {
    this.paginationManager = new PaginationManager({
      itemsPerPage: 6,
      maxFields: 5
    });
  }

  updateData(movies: MovieDownloadItem[], tv: TVDownloadItem[], total: number): {
    embed: EmbedBuilder;
    components: ActionRowBuilder<ButtonBuilder>[];
  } {
    this.movies = movies;
    this.tv = tv;
    this.total = total;

    return this.paginationManager.createPaginatedEmbed(movies, tv, total);
  }

  async handleButtonInteraction(interaction: ButtonInteraction): Promise<void> {
    if (!interaction.customId.startsWith('pagination_')) {
      return;
    }

    // Handle pagination
    const changed = this.paginationManager.handleButton(interaction.customId);
    
    if (changed) {
      const { embed, components } = this.paginationManager.createPaginatedEmbed(
        this.movies,
        this.tv,
        this.total
      );

      await interaction.update({
        embeds: [embed],
        components
      });
    } else {
      // Acknowledge the interaction even if no change
      await interaction.deferUpdate();
    }
  }

  isValidInteraction(customId: string): boolean {
    return customId.startsWith('pagination_');
  }
}