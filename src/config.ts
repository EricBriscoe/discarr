import { config } from 'dotenv';

config();

export interface Config {
  discord: {
    token: string;
    channelId: string;
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
  };
  monitoring: {
    checkInterval: number;
    healthCheckInterval: number;
    verbose: boolean;
  };
}

function getConfig(): Config {
  const requiredEnvVars = ['DISCORD_TOKEN', 'DISCORD_CHANNEL_ID'];
  
  for (const envVar of requiredEnvVars) {
    if (!process.env[envVar]) {
      throw new Error(`Missing required environment variable: ${envVar}`);
    }
  }

  return {
    discord: {
      token: process.env.DISCORD_TOKEN!,
      channelId: process.env.DISCORD_CHANNEL_ID!,
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
    },
    monitoring: {
      checkInterval: parseInt(process.env.CHECK_INTERVAL || '300') * 1000,
      healthCheckInterval: parseInt(process.env.HEALTH_CHECK_INTERVAL || '60') * 1000,
      verbose: process.env.VERBOSE === 'true',
    },
  };
}

export default getConfig();