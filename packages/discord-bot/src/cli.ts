import { DiscarrBot } from './lib/bot';

async function main() {
  const enableBot = process.env.ENABLE_DISCORD_BOT !== 'false';
  if (!enableBot) {
    console.log('Discord bot disabled via ENABLE_DISCORD_BOT=false');
    return;
  }
  console.log('Starting Discarr Discord Bot...');
  const bot = new DiscarrBot();
  await bot.start();
}

main().catch((err) => {
  console.error('Bot failed to start:', err);
  process.exit(1);
});

