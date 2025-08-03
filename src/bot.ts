import { Client, GatewayIntentBits, TextChannel, Message, Interaction, REST, Routes } from 'discord.js';
import { HealthMonitor } from './monitoring/health-monitor';
import { DownloadMonitor } from './monitoring/download-monitor';
import { DiscordEmbedBuilder } from './discord/embed-builder';
import { DownloadView } from './discord/download-view';
import { CleanupCommand, CalendarCommand, SeriesSearchCommand } from './discord/commands';
import { QBittorrentClient } from './services/qbittorrent-client.js';
import { SonarrClient } from './services/sonarr-client.js';
import config from './config';

export class DiscarrBot {
  private client: Client;
  private healthMonitor: HealthMonitor;
  private downloadMonitor: DownloadMonitor;
  private downloadView: DownloadView;
  private cleanupCommand: CleanupCommand;
  private calendarCommand: CalendarCommand;
  private seriesSearchCommand: SeriesSearchCommand;
  private channel?: TextChannel;
  private currentHealthMessage?: Message;
  private currentDownloadsMessage?: Message;
  private healthCheckInterval?: NodeJS.Timeout;

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
    
    this.cleanupCommand = new CleanupCommand(qbittorrentClient);
    this.calendarCommand = new CalendarCommand(sonarrClient);
    this.seriesSearchCommand = new SeriesSearchCommand(sonarrClient);

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
          }
        } catch (error) {
          console.error('❌ Error handling button interaction:', error);
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
        this.seriesSearchCommand.data.toJSON()
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
        downloads.movies,
        downloads.tv,
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

    // Download monitoring with pagination
    this.downloadMonitor.startMonitoring(async (downloads) => {
      try {
        const { embed: downloadsEmbed, components } = this.downloadView.updateData(
          downloads.movies,
          downloads.tv,
          downloads.total
        );

        if (this.currentDownloadsMessage) {
          await this.currentDownloadsMessage.edit({ 
            embeds: [downloadsEmbed],
            components
          });
        }
      } catch (error) {
        console.error('❌ Error updating downloads:', error);
      }
    });

    console.log('🔄 Monitoring started');
  }

  private async shutdown(): Promise<void> {
    console.log('🛑 Shutting down bot...');
    
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
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