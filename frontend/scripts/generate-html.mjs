import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

async function generateHtml() {
  try {
    const serverEntryPath = path.resolve(process.cwd(), '.output/server/index.mjs');
    const { default: handler } = await import(pathToFileURL(serverEntryPath).href);

    const req = new Request('http://localhost/', {
      headers: {
        accept: 'text/html',
      },
    });

    const env = {
      ASSETS: {
        fetch: async () => new Response('Not found', { status: 404 }),
      },
    };

    const ctx = {
      waitUntil: () => {},
      passThroughOnException: () => {},
    };

    const res = await handler.fetch(req, env, ctx);
    if (!res.ok) {
      throw new Error(`SSR fetch returned status ${res.status}`);
    }

    const html = await res.text();
    const outputPath = path.resolve(process.cwd(), '.output/public/index.html');
    await fs.writeFile(outputPath, html, 'utf-8');
    console.log(`[generate-html] Successfully generated ${outputPath} (${html.length} bytes)`);
  } catch (err) {
    console.error('[generate-html] Failed to generate index.html:', err);
    process.exit(1);
  }
}

generateHtml();
