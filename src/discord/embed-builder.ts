import { EmbedBuilder } from 'discord.js';
import { HealthStatus, MovieDownloadItem, TVDownloadItem } from '../types';
import { QBittorrentClient } from '../services/qbittorrent-client';

export class DiscordEmbedBuilder {
  static createHealthEmbed(healthStatus: HealthStatus): EmbedBuilder {
    console.log('📋 Creating health embed...');
    console.log('📊 Health status received:', {
      plex: healthStatus.plex?.status,
      radarr: healthStatus.radarr?.status,
      sonarr: healthStatus.sonarr?.status,
      qbittorrent: healthStatus.qbittorrent?.status,
      lastUpdated: healthStatus.lastUpdated
    });

    const embed = new EmbedBuilder()
      .setTitle('🏥 Service Health Status')
      .setTimestamp(healthStatus.lastUpdated)
      .setColor(this.getHealthColor(healthStatus));

    // Add service status fields
    if (healthStatus.plex) {
      const emoji = this.getStatusEmoji(healthStatus.plex.status);
      const responseTime = healthStatus.plex.responseTime 
        ? ` (${healthStatus.plex.responseTime}ms)` 
        : '';
      embed.addFields({
        name: '🎞️ Plex Media Server',
        value: `${emoji} ${healthStatus.plex.status}${responseTime}`,
        inline: false,
      });
    }

    if (healthStatus.radarr) {
      const emoji = this.getStatusEmoji(healthStatus.radarr.status);
      const responseTime = healthStatus.radarr.responseTime 
        ? ` (${healthStatus.radarr.responseTime}ms)` 
        : '';
      const version = healthStatus.radarr.version ? ` v${healthStatus.radarr.version}` : '';
      embed.addFields({
        name: '🎬 Radarr',
        value: `${emoji} ${healthStatus.radarr.status}${responseTime}${version}`,
        inline: false,
      });
    }

    if (healthStatus.sonarr) {
      const emoji = this.getStatusEmoji(healthStatus.sonarr.status);
      const responseTime = healthStatus.sonarr.responseTime 
        ? ` (${healthStatus.sonarr.responseTime}ms)` 
        : '';
      const version = healthStatus.sonarr.version ? ` v${healthStatus.sonarr.version}` : '';
      embed.addFields({
        name: '📺 Sonarr',
        value: `${emoji} ${healthStatus.sonarr.status}${responseTime}${version}`,
        inline: false,
      });
    }

    if (healthStatus.qbittorrent) {
      console.log('🏴‍☠️ Processing qBittorrent section...');
      console.log('📊 qBittorrent data:', healthStatus.qbittorrent);
      
      const emoji = this.getStatusEmoji(healthStatus.qbittorrent.status);
      const responseTime = healthStatus.qbittorrent.responseTime 
        ? ` (${healthStatus.qbittorrent.responseTime}ms)` 
        : '';
      
      let value = `${emoji} ${healthStatus.qbittorrent.status}${responseTime}`;

      // Add transfer info if available
      if (healthStatus.qbittorrent.transferInfo) {
        console.log('📈 Adding transfer info to embed...');
        const transferInfo = healthStatus.qbittorrent.transferInfo;
        const dlSpeed = QBittorrentClient.formatSpeed(transferInfo.dl_info_speed);
        const upSpeed = QBittorrentClient.formatSpeed(transferInfo.up_info_speed);
        
        if (transferInfo.dl_info_speed > 0 || transferInfo.up_info_speed > 0) {
          value += `\n🔽 ${dlSpeed} • 🔼 ${upSpeed}`;
        }

        // Add session totals
        const sessionDL = QBittorrentClient.formatBytes(transferInfo.dl_info_data);
        const sessionUP = QBittorrentClient.formatBytes(transferInfo.up_info_data);
        value += `\n📊 Session: ${sessionDL} ⬇️ • ${sessionUP} ⬆️`;

        // Add connection info
        const connectionEmoji = transferInfo.connection_status === 'connected' ? '⚡' : '🔥';
        const dhtNodes = transferInfo.dht_nodes > 0 ? `🌐 ${transferInfo.dht_nodes} DHT nodes • ` : '';
        value += `\n${dhtNodes}${connectionEmoji} ${transferInfo.connection_status}`;
      }

      // Add torrent stats if available
      if (healthStatus.qbittorrent.torrentStats) {
        console.log('🎯 Adding torrent stats to embed...');
        const stats = healthStatus.qbittorrent.torrentStats;
        const activeParts = [];
        
        if (stats.downloading > 0) activeParts.push(`📥 ${stats.downloading} downloading`);
        if (stats.seeding > 0) activeParts.push(`🌱 ${stats.seeding} seeding`);
        if (stats.queued > 0) activeParts.push(`⏳ ${stats.queued} queued`);
        if (stats.stalled > 0) activeParts.push(`⚠️ ${stats.stalled} stalled`);
        if (stats.error > 0) activeParts.push(`❌ ${stats.error} error`);

        if (activeParts.length > 0) {
          value += `\n${activeParts.join(' • ')}`;
        }
      }

      console.log('➕ Adding qBittorrent field to embed with value:', value);
      embed.addFields({
        name: '🏴‍☠️ qBittorrent',
        value,
        inline: false,
      });
    } else {
      console.log('❌ No qBittorrent data in healthStatus');
    }

    return embed;
  }

  static createDownloadsEmbed(
    movies: MovieDownloadItem[], 
    tv: TVDownloadItem[], 
    total: number
  ): EmbedBuilder {
    const embed = new EmbedBuilder()
      .setTitle('📥 Active Downloads')
      .setTimestamp()
      .setColor(0x00ff00);

    if (total === 0) {
      embed.setDescription('No active downloads');
      embed.setColor(0x808080);
      return embed;
    }

    // Add movies section
    if (movies.length > 0) {
      const movieList = movies.slice(0, 5).map(movie => {
        const progressBar = this.createProgressBar(movie.progress);
        const timeLeft = movie.timeLeft || '∞';
        const status = movie.status === 'downloading' ? '⬇️' : '⏸️';
        return `${status} **${this.truncateTitle(movie.title)}**\n${progressBar} ${movie.progress.toFixed(1)}% • ${timeLeft}`;
      }).join('\n\n');

      embed.addFields({
        name: `🎬 Movies (${movies.length})`,
        value: movieList,
        inline: false,
      });
    }

    // Add TV section
    if (tv.length > 0) {
      const tvList = tv.slice(0, 5).map(show => {
        const progressBar = this.createProgressBar(show.progress);
        const timeLeft = show.timeLeft || '∞';
        const status = show.status === 'downloading' ? '⬇️' : '⏸️';
        return `${status} **${this.truncateTitle(show.title)}**\n${progressBar} ${show.progress.toFixed(1)}% • ${timeLeft}`;
      }).join('\n\n');

      embed.addFields({
        name: `📺 TV Shows (${tv.length})`,
        value: tvList,
        inline: false,
      });
    }

    if (total > 10) {
      embed.setFooter({ text: `Showing top 10 of ${total} downloads` });
    }

    return embed;
  }

  private static getStatusEmoji(status: string): string {
    const emojis = {
      online: '🟢',
      offline: '🔴',
      error: '🟡',
    };
    return emojis[status as keyof typeof emojis] || '❓';
  }

  private static getHealthColor(healthStatus: HealthStatus): number {
    const services = [healthStatus.plex, healthStatus.radarr, healthStatus.sonarr, healthStatus.qbittorrent]
      .filter(Boolean);

    if (services.some(service => service?.status === 'offline')) {
      return 0xff0000; // Red
    }
    if (services.some(service => service?.status === 'error')) {
      return 0xffa500; // Orange
    }
    return 0x00ff00; // Green
  }

  private static createProgressBar(progress: number, length = 10): string {
    const filled = Math.round((progress / 100) * length);
    const empty = length - filled;
    return '█'.repeat(filled) + '░'.repeat(empty);
  }

  private static truncateTitle(title: string, maxLength = 40): string {
    return title.length > maxLength ? `${title.substring(0, maxLength - 3)}...` : title;
  }
}