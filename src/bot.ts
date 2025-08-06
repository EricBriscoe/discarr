import { Client, GatewayIntentBits, TextChannel, Message, Interaction, REST, Routes, StringSelectMenuInteraction, EmbedBuilder, MessageFlags, ButtonInteraction } from 'discord.js';
import { HealthMonitor } from './monitoring/health-monitor';
import { DownloadMonitor } from './monitoring/download-monitor';
import { DiscordEmbedBuilder } from './discord/embed-builder';
import { DownloadView } from './discord/download-view';
import { CleanupCommand, CalendarCommand, SeriesSearchCommand, UnblockCommand } from './discord/commands';
import { QBittorrentClient } from './services/qbittorrent-client.js';
import { SonarrClient } from './services/sonarr-client.js';
import { RadarrClient } from './services/radarr-client.js';
import config from './config';

export class DiscarrBot {
  private client: Client;
  private healthMonitor: HealthMonitor;
  private downloadMonitor: DownloadMonitor;
  private downloadView: DownloadView;
  private cleanupCommand: CleanupCommand;
  private calendarCommand: CalendarCommand;
  private seriesSearchCommand: SeriesSearchCommand;
  private unblockCommand: UnblockCommand;
  private channel?: TextChannel;
  private currentHealthMessage?: Message;
  private currentDownloadsMessage?: Message;
  private healthCheckInterval?: NodeJS.Timeout;
  private downloadCheckTimeout?: NodeJS.Timeout;

  constructor() {
    this.client = new Client({
      intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
    });

    this.healthMonitor = new HealthMonitor();
    this.downloadMonitor = new DownloadMonitor(this.healthMonitor);
    this.downloadView = new DownloadView();
    
    if (!config.services.qbittorrent) {
      throw new Error('qBittorrent configuration is required for cleanup command');
    }
    
    if (!config.services.sonarr) {
      throw new Error('Sonarr configuration is required for calendar and series search commands');
    }

    if (!config.services.radarr) {
      throw new Error('Radarr configuration is required for unblock command');
    }
    
    const qbittorrentClient = new QBittorrentClient({
      baseUrl: config.services.qbittorrent.url,
      username: config.services.qbittorrent.username,
      password: config.services.qbittorrent.password
    });
    
    const sonarrClient = new SonarrClient(
      config.services.sonarr.url,
      config.services.sonarr.apiKey,
      config.monitoring.verbose
    );

    const radarrClient = new RadarrClient(
      config.services.radarr.url,
      config.services.radarr.apiKey,
      config.monitoring.verbose
    );
    
    this.cleanupCommand = new CleanupCommand(qbittorrentClient);
    this.calendarCommand = new CalendarCommand(sonarrClient);
    this.seriesSearchCommand = new SeriesSearchCommand(sonarrClient);
    this.unblockCommand = new UnblockCommand(radarrClient, sonarrClient);

    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    this.client.once('ready', async () => {
      console.log(`✅ Bot logged in as ${this.client.user?.tag}`);
      
      try {
        await this.registerSlashCommands();
        
        this.channel = await this.client.channels.fetch(config.discord.channelId) as TextChannel;
        console.log(`📍 Connected to channel: ${this.channel.name}`);
        
        await this.cleanupPreviousMessages();
        await this.initializeMessages();
        this.startMonitoring();
      } catch (error) {
        console.error('❌ Error during bot initialization:', error);
        process.exit(1);
      }
    });

    this.client.on('interactionCreate', async (interaction) => {
      if (interaction.isButton()) {
        try {
          if (this.downloadView.isValidInteraction(interaction.customId)) {
            await this.downloadView.handleButtonInteraction(interaction);
          } else if (interaction.customId.startsWith('unblock_')) {
            await this.handleUnblockButtonInteraction(interaction);
          }
        } catch (error) {
          console.error('❌ Error handling button interaction:', error);
        }
      } else if (interaction.isStringSelectMenu()) {
        try {
          if (interaction.customId.startsWith('search_series_')) {
            await this.handleSeriesSearchMenu(interaction);
          }
        } catch (error) {
          console.error('❌ Error handling select menu interaction:', error);
        }
      } else if (interaction.isChatInputCommand()) {
        try {
          switch (interaction.commandName) {
            case 'cleanup':
              await this.cleanupCommand.execute(interaction);
              break;
            case 'calendar':
              await this.calendarCommand.execute(interaction);
              break;
            case 'series-search':
              await this.seriesSearchCommand.execute(interaction);
              break;
            case 'unblock':
              await this.unblockCommand.execute(interaction);
              break;
          }
        } catch (error) {
          console.error('❌ Error handling command interaction:', error);
        }
      }
    });

    this.client.on('error', (error) => {
      console.error('❌ Discord client error:', error);
    });

    process.on('SIGINT', () => this.shutdown());
    process.on('SIGTERM', () => this.shutdown());
  }

  private async registerSlashCommands(): Promise<void> {
    try {
      const rest = new REST({ version: '10' }).setToken(config.discord.token);
      
      const commands = [
        this.cleanupCommand.data.toJSON(),
        this.calendarCommand.data.toJSON(),
        this.seriesSearchCommand.data.toJSON(),
        this.unblockCommand.data.toJSON()
      ];

      console.log('🔄 Registering slash commands...');
      
      await rest.put(
        Routes.applicationCommands(config.discord.clientId),
        { body: commands }
      );

      console.log('✅ Slash commands registered successfully');
    } catch (error) {
      console.error('❌ Error registering slash commands:', error);
    }
  }

  private async cleanupPreviousMessages(): Promise<void> {
    if (!this.channel) return;

    try {
      const messages = await this.channel.messages.fetch({ limit: 100 });
      const botMessages = messages.filter(msg => 
        msg.author.id === this.client.user?.id && 
        msg.embeds.length > 0
      );

      if (botMessages.size > 0) {
        await this.channel.bulkDelete(botMessages);
        console.log(`🧹 Cleaned up ${botMessages.size} previous messages`);
      }
    } catch (error) {
      console.error('⚠️ Error cleaning up messages:', error);
    }
  }

  private async initializeMessages(): Promise<void> {
    if (!this.channel) return;

    try {
      // Create initial health message
      const healthStatus = await this.healthMonitor.checkAllServices();
      const healthEmbed = DiscordEmbedBuilder.createHealthEmbed(healthStatus);
      this.currentHealthMessage = await this.channel.send({ embeds: [healthEmbed] });

      // Create initial downloads message with pagination
      const downloads = await this.downloadMonitor.getActiveDownloads();
      const { embed: downloadsEmbed, components } = this.downloadView.updateData(
        downloads.items,
        downloads.total
      );
      this.currentDownloadsMessage = await this.channel.send({ 
        embeds: [downloadsEmbed],
        components
      });

      console.log('📨 Initial messages created');
    } catch (error) {
      console.error('❌ Error creating initial messages:', error);
    }
  }

  private startMonitoring(): void {
    // Health monitoring
    this.healthCheckInterval = setInterval(async () => {
      try {
        const healthStatus = await this.healthMonitor.checkAllServices();
        const healthEmbed = DiscordEmbedBuilder.createHealthEmbed(healthStatus);
        
        if (this.currentHealthMessage) {
          await this.currentHealthMessage.edit({ embeds: [healthEmbed] });
        }
      } catch (error) {
        console.error('❌ Error updating health status:', error);
      }
    }, config.monitoring.healthCheckInterval);

    // Start smart download monitoring
    this.startSmartDownloadMonitoring();

    console.log('🔄 Monitoring started');
  }

  private startSmartDownloadMonitoring(): void {
    const updateDownloads = async () => {
      try {
        const downloads = await this.downloadMonitor.getActiveDownloads();
        
        // Update the Discord message
        const { embed: downloadsEmbed, components } = this.downloadView.updateData(
          downloads.items,
          downloads.total
        );

        if (this.currentDownloadsMessage) {
          await this.currentDownloadsMessage.edit({ 
            embeds: [downloadsEmbed],
            components
          });
        }

        // Calculate smart refresh interval
        const nextInterval = this.downloadMonitor.calculateNextRefreshInterval(downloads);
        
        if (config.monitoring.verbose) {
          console.log(`📊 Downloads updated. Next refresh in ${Math.round(nextInterval / 1000)}s`);
        }

        // Schedule next update with dynamic interval
        this.downloadCheckTimeout = setTimeout(updateDownloads, nextInterval);

      } catch (error) {
        console.error('❌ Error in smart download monitoring:', error);
        throw error;
      }
    };

    // Start immediately
    updateDownloads();
  }

  private async handleSeriesSearchMenu(interaction: StringSelectMenuInteraction): Promise<void> {
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });

    const seriesId = parseInt(interaction.customId.split('_')[2]);
    const value = interaction.values[0];

    if (value === 'cancel') {
      // Remove the select menu from the original message
      await interaction.message.edit({ 
        embeds: interaction.message.embeds, 
        components: [] 
      });
      
      const embed = new EmbedBuilder()
        .setTitle('❌ Search Cancelled')
        .setDescription('Search cancelled. The missing episodes list remains displayed.')
        .setColor(0x666666)
        .setTimestamp();

      await interaction.editReply({ embeds: [embed] });
      return;
    }

    if (value === 'start_search') {
      // Get the Sonarr client from the series search command
      const sonarrClient = this.seriesSearchCommand.sonarrClient;
      
      const embed = new EmbedBuilder()
        .setTitle('🔍 Starting Search...')
        .setDescription('Triggering search for missing episodes in Sonarr...')
        .setColor(0xffaa00)
        .setTimestamp();

      await interaction.editReply({ embeds: [embed] });

      try {
        const success = await sonarrClient.searchForMissingEpisodes(seriesId);
        
        if (success) {
          embed
            .setTitle('✅ Search Started')
            .setDescription('Successfully triggered search for missing episodes! Check Sonarr for progress.')
            .setColor(0x00ff00);
        } else {
          embed
            .setTitle('❌ Search Failed')
            .setDescription('Failed to trigger search in Sonarr. Check logs for details.')
            .setColor(0xff0000);
        }

        await interaction.editReply({ embeds: [embed] });

        // Remove the select menu from the original message
        await interaction.message.edit({ 
          embeds: interaction.message.embeds, 
          components: [] 
        });

      } catch (error) {
        console.error('Error starting series search:', error);
        
        embed
          .setTitle('❌ Search Error')
          .setDescription(`Error starting search: ${error instanceof Error ? error.message : 'Unknown error'}`)
          .setColor(0xff0000);

        await interaction.editReply({ embeds: [embed] });
      }
    }
  }

  private async handleUnblockButtonInteraction(interaction: ButtonInteraction): Promise<void> {
    const customId = interaction.customId;
    const parts = customId.split('_'); // Expected format: unblock_{action}_{service}_{itemId}_{currentIndex}
    
    if (parts.length !== 5) {
      console.error('Invalid unblock button customId format:', customId);
      return;
    }

    const [, action, service, itemIdStr, currentIndexStr] = parts;
    const itemId = parseInt(itemIdStr);
    const currentIndex = parseInt(currentIndexStr);

    if (isNaN(itemId) || isNaN(currentIndex)) {
      console.error('Invalid itemId or currentIndex in button interaction:', customId);
      return;
    }

    // Get the original message to extract blocked items data
    // For simplicity, we'll fetch blocked items again
    try {
      const [radarrBlocked, sonarrBlocked] = await Promise.all([
        this.unblockCommand['radarrClient'].getImportBlockedItems(),
        this.unblockCommand['sonarrClient'].getImportBlockedItems()
      ]);

      const allBlocked = [
        ...radarrBlocked.map(item => ({ ...item, service: 'radarr' as const })),
        ...sonarrBlocked.map(item => ({ ...item, service: 'sonarr' as const }))
      ];

      // Initialize processed count - in a real implementation you'd want to track this state
      const processedCount = { approved: 0, rejected: 0, skipped: 0 };

      await this.unblockCommand.handleButtonInteraction(
        interaction, 
        action, 
        service as 'radarr' | 'sonarr', 
        itemId, 
        currentIndex,
        allBlocked,
        processedCount
      );

    } catch (error) {
      console.error('Error handling unblock button interaction:', error);
      
      await interaction.reply({
        content: '❌ Error processing request. Please try the /unblock command again.',
        ephemeral: true
      });
    }
  }

  private async shutdown(): Promise<void> {
    console.log('🛑 Shutting down bot...');
    
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }
    
    if (this.downloadCheckTimeout) {
      clearTimeout(this.downloadCheckTimeout);
    }
    
    this.downloadMonitor.stopMonitoring();
    await this.client.destroy();
    
    console.log('✅ Bot shutdown complete');
    process.exit(0);
  }

  async start(): Promise<void> {
    try {
      await this.client.login(config.discord.token);
    } catch (error) {
      console.error('❌ Failed to start bot:', error);
      process.exit(1);
    }
  }
}