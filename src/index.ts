import { DiscarrBot } from './bot';

async function main() {
  console.log('🚀 Starting Discarr Discord Bot v2.0...');
  
  try {
    const bot = new DiscarrBot();
    await bot.start();
  } catch (error) {
    console.error('❌ Failed to start bot:', error);
    process.exit(1);
  }
}

main();