import type { Config } from '@discarr/core/src/config';
import { DiscarrBot } from '@discarr/discord-bot';

export class BotController {
  private bot?: DiscarrBot;
  get running() { return !!this.bot; }

  async start(config: Config) {
    if (this.bot) return; // already running
    this.bot = new DiscarrBot(config);
    await this.bot.start();
  }

  async stop() {
    if (!this.bot) return;
    await this.bot.stop();
    this.bot = undefined;
  }

  async restart(config: Config) {
    await this.stop();
    await this.start(config);
  }
}

