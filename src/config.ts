import { config } from 'dotenv';

config();

export interface Config {
  discord: {
    token: string;
    channelId: string;
    clientId: string;
  };
  services: {
    radarr?: {
      url: string;
      apiKey: string;
    };
    sonarr?: {
      url: string;
      apiKey: string;
    };
    plex?: {
      url: string;
    };
    qbittorrent?: {
      url: string;
      username: string;
      password: string;
    };
  };
  monitoring: {
    checkInterval: number;
    healthCheckInterval: number;
    verbose: boolean;
    minRefreshInterval: number;
    maxRefreshInterval: number;
  };
}

function getConfig(): Config {
  const requiredEnvVars = ['DISCORD_TOKEN', 'DISCORD_CHANNEL_ID', 'DISCORD_CLIENT_ID'];
  
  for (const envVar of requiredEnvVars) {
    if (!process.env[envVar]) {
      throw new Error(`Missing required environment variable: ${envVar}`);
    }
  }

  return {
    discord: {
      token: process.env.DISCORD_TOKEN!,
      channelId: process.env.DISCORD_CHANNEL_ID!,
      clientId: process.env.DISCORD_CLIENT_ID!,
    },
    services: {
      ...(process.env.RADARR_URL && process.env.RADARR_API_KEY && {
        radarr: {
          url: process.env.RADARR_URL,
          apiKey: process.env.RADARR_API_KEY,
        },
      }),
      ...(process.env.SONARR_URL && process.env.SONARR_API_KEY && {
        sonarr: {
          url: process.env.SONARR_URL,
          apiKey: process.env.SONARR_API_KEY,
        },
      }),
      ...(process.env.PLEX_URL && {
        plex: {
          url: process.env.PLEX_URL,
        },
      }),
      ...(process.env.QBITTORRENT_URL && process.env.QBITTORRENT_USERNAME && process.env.QBITTORRENT_PASSWORD && {
        qbittorrent: {
          url: process.env.QBITTORRENT_URL,
          username: process.env.QBITTORRENT_USERNAME,
          password: process.env.QBITTORRENT_PASSWORD,
        },
      }),
    },
    monitoring: {
      checkInterval: parseInt(process.env.CHECK_INTERVAL || '300') * 1000,
      healthCheckInterval: parseInt(process.env.HEALTH_CHECK_INTERVAL || '60') * 1000,
      verbose: process.env.VERBOSE === 'true',
      minRefreshInterval: parseInt(process.env.MIN_REFRESH_INTERVAL || '30') * 1000, // 30 seconds
      maxRefreshInterval: parseInt(process.env.MAX_REFRESH_INTERVAL || '600') * 1000, // 10 minutes
    },
  };
}

export default getConfig();