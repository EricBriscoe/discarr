import { EmbedBuilder } from 'discord.js';
import { HealthStatus } from '@discarr/core';
import { QBittorrentClient } from '@discarr/core';

export class DiscordEmbedBuilder {
  static createHealthEmbed(healthStatus: HealthStatus): EmbedBuilder {
    const embed = new EmbedBuilder()
      .setTitle('🏥 Service Health Status')
      .setTimestamp(healthStatus.lastUpdated)
      .setColor(this.getHealthColor(healthStatus));

    if (healthStatus.plex) {
      const emoji = this.getStatusEmoji(healthStatus.plex.status);
      const responseTime = healthStatus.plex.responseTime ? ` (${healthStatus.plex.responseTime}ms)` : '';
      embed.addFields({ name: '🎞️ Plex Media Server', value: `${emoji} ${healthStatus.plex.status}${responseTime}`, inline: false });
    }
    if (healthStatus.radarr) {
      const emoji = this.getStatusEmoji(healthStatus.radarr.status);
      const responseTime = healthStatus.radarr.responseTime ? ` (${healthStatus.radarr.responseTime}ms)` : '';
      const version = healthStatus.radarr.version ? ` v${healthStatus.radarr.version}` : '';
      embed.addFields({ name: '🎬 Radarr', value: `${emoji} ${healthStatus.radarr.status}${responseTime}${version}`, inline: false });
    }
    if (healthStatus.sonarr) {
      const emoji = this.getStatusEmoji(healthStatus.sonarr.status);
      const responseTime = healthStatus.sonarr.responseTime ? ` (${healthStatus.sonarr.responseTime}ms)` : '';
      const version = healthStatus.sonarr.version ? ` v${healthStatus.sonarr.version}` : '';
      embed.addFields({ name: '📺 Sonarr', value: `${emoji} ${healthStatus.sonarr.status}${responseTime}${version}`, inline: false });
    }
    if (healthStatus.qbittorrent) {
      const emoji = this.getStatusEmoji(healthStatus.qbittorrent.status);
      const responseTime = healthStatus.qbittorrent.responseTime ? ` (${healthStatus.qbittorrent.responseTime}ms)` : '';
      let value = `${emoji} ${healthStatus.qbittorrent.status}${responseTime}`;
      if (healthStatus.qbittorrent.transferInfo) {
        const transferInfo = healthStatus.qbittorrent.transferInfo;
        const dlSpeed = QBittorrentClient.formatSpeed(transferInfo.dl_info_speed);
        const upSpeed = QBittorrentClient.formatSpeed(transferInfo.up_info_speed);
        if (transferInfo.dl_info_speed > 0 || transferInfo.up_info_speed > 0) {
          value += `\n🔽 ${dlSpeed} • 🔼 ${upSpeed}`;
        }
        const sessionDL = QBittorrentClient.formatBytes(transferInfo.dl_info_data);
        const sessionUP = QBittorrentClient.formatBytes(transferInfo.up_info_data);
        value += `\n📊 Session: ${sessionDL} ⬇️ • ${sessionUP} ⬆️`;
        const connectionEmoji = transferInfo.connection_status === 'connected' ? '⚡' : '🔥';
        const dhtNodes = transferInfo.dht_nodes > 0 ? `🌐 ${transferInfo.dht_nodes} DHT nodes • ` : '';
        value += `\n${dhtNodes}${connectionEmoji} ${transferInfo.connection_status}`;
      }
      if (healthStatus.qbittorrent.torrentStats) {
        const stats = healthStatus.qbittorrent.torrentStats;
        const parts = [] as string[];
        if (stats.downloading > 0) parts.push(`📥 ${stats.downloading} downloading`);
        if (stats.seeding > 0) parts.push(`🌱 ${stats.seeding} seeding`);
        if (stats.queued > 0) parts.push(`⏳ ${stats.queued} queued`);
        if (stats.stalled > 0) parts.push(`⚠️ ${stats.stalled} stalled`);
        if (stats.error > 0) parts.push(`❌ ${stats.error} error`);
        if (parts.length > 0) value += `\n${parts.join(' • ')}`;
      }
      embed.addFields({ name: '⚡ qBittorrent', value, inline: false });
    }
    return embed;
  }

  private static getStatusEmoji(status: string): string {
    const emojis = { online: '🟢', offline: '🔴', error: '🟡' } as const;
    return (emojis as any)[status] || '❓';
  }

  private static getHealthColor(healthStatus: HealthStatus): number {
    const services = [healthStatus.plex, healthStatus.radarr, healthStatus.sonarr, healthStatus.qbittorrent].filter(Boolean) as any[];
    if (services.some(s => s?.status === 'offline')) return 0xff0000;
    if (services.some(s => s?.status === 'error')) return 0xffa500;
    return 0x00ff00;
  }
}

