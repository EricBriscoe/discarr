import { ActionRowBuilder, ButtonBuilder, ButtonInteraction, EmbedBuilder } from 'discord.js';
import { PaginationManager } from './pagination';
import { AnyDownloadItem } from '../types';

export class DownloadView {
  private paginationManager: PaginationManager;
  private items: AnyDownloadItem[] = [];
  private total = 0;

  constructor() {
    this.paginationManager = new PaginationManager({
      itemsPerPage: 6,
      maxFields: 5
    });
  }

  updateData(items: AnyDownloadItem[], total: number): {
    embed: EmbedBuilder;
    components: ActionRowBuilder<ButtonBuilder>[];
  } {
    this.items = items;
    this.total = total;

    return this.paginationManager.createPaginatedEmbed(items, total);
  }

  async handleButtonInteraction(interaction: ButtonInteraction): Promise<void> {
    if (!interaction.customId.startsWith('pagination_')) {
      return;
    }

    // Handle pagination
    const changed = this.paginationManager.handleButton(interaction.customId);
    
    if (changed) {
      const { embed, components } = this.paginationManager.createPaginatedEmbed(
        this.items,
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