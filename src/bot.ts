import { Client, GatewayIntentBits, TextChannel, Message } from 'discord.js';
import { HealthMonitor } from './monitoring/health-monitor';
import { DownloadMonitor } from './monitoring/download-monitor';
import { DiscordEmbedBuilder } from './discord/embed-builder';
import config from './config';

export class DiscarrBot {
  private client: Client;
  private healthMonitor: HealthMonitor;
  private downloadMonitor: DownloadMonitor;
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

    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    this.client.once('ready', async () => {
      console.log(`✅ Bot logged in as ${this.client.user?.tag}`);
      
      try {
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

    this.client.on('error', (error) => {
      console.error('❌ Discord client error:', error);
    });

    process.on('SIGINT', () => this.shutdown());
    process.on('SIGTERM', () => this.shutdown());
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

      // Create initial downloads message
      const downloads = await this.downloadMonitor.getActiveDownloads();
      const downloadsEmbed = DiscordEmbedBuilder.createDownloadsEmbed(
        downloads.movies, 
        downloads.tv, 
        downloads.total
      );
      this.currentDownloadsMessage = await this.channel.send({ embeds: [downloadsEmbed] });

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

    // Download monitoring
    this.downloadMonitor.startMonitoring(async (downloads) => {
      try {
        const downloadsEmbed = DiscordEmbedBuilder.createDownloadsEmbed(
          downloads.movies,
          downloads.tv,
          downloads.total
        );

        if (this.currentDownloadsMessage) {
          await this.currentDownloadsMessage.edit({ embeds: [downloadsEmbed] });
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