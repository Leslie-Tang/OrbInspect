// Read-only native draw.io export QA through its documented embed protocol.
// Usage: node verify_drawio_export.cjs INPUT.drawio QA_DIR CHROME_EXECUTABLE
// Requires playwright. No existing browser profile or editor session is touched.
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const {chromium} = require('playwright');

async function main() {
  const [source, destination, executablePath] = process.argv.slice(2);
  const xml = fs.readFileSync(source, 'utf8');
  const html = `<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0"><iframe id="editor"
    style="width:1800px;height:1000px;border:0"
    src="https://embed.diagrams.net/?embed=1&proto=json&spin=1&ui=min&dark=0"></iframe>
    <script>window.events=[];const xml=${JSON.stringify(xml).replaceAll('<','\\u003c')};
    addEventListener('message', e=>{if(e.origin!=='https://embed.diagrams.net')return;
      let m;try{m=JSON.parse(e.data)}catch{return}window.events.push(m.event);
      const send=m=>e.source.postMessage(JSON.stringify(m),e.origin);
      if(m.event==='init')send({action:'load',xml,fit:1,theme:'light',background:'#ffffff'});
      if(m.event==='load')setTimeout(()=>send({action:'export',format:'svg',
        background:'#ffffff',theme:'light',border:14,embedFonts:true}),2500);
      if(m.event==='export')window.result=m;
    });</script></body></html>`;
  const server = http.createServer((req,res)=>{res.setHeader('Content-Type','text/html; charset=utf-8');res.end(html)});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let browser;
  try {
    browser = await chromium.launch({executablePath,headless:true,timeout:20000});
    const page = await browser.newPage({viewport:{width:1840,height:1040}});
    await page.goto(`http://127.0.0.1:${server.address().port}`,{waitUntil:'domcontentloaded'});
    await page.waitForFunction(()=>window.result, {timeout:45000});
    const result = await page.evaluate(()=>({result:window.result,events:window.events}));
    const data = result.result.data;
    if (!data?.startsWith('data:image/svg+xml')) throw new Error('Native SVG export was not returned');
    const svg = data.slice(0,data.indexOf(',')).includes('base64')
      ? Buffer.from(data.slice(data.indexOf(',')+1),'base64').toString()
      : decodeURIComponent(data.slice(data.indexOf(',')+1));
    fs.mkdirSync(destination,{recursive:true});
    fs.writeFileSync(path.join(destination,'native-export.svg'),svg);
    fs.writeFileSync(path.join(destination,'native-roundtrip.drawio'),result.result.xml);
    const review=await browser.newPage({viewport:{width:1800,height:840}});
    await review.setContent(svg,{waitUntil:'load'});
    await review.evaluate(()=>document.fonts.ready);
    const errors=await review.locator('[data-mml-node="merror"],mjx-merror').count();
    const math=await review.locator('mjx-container').count();
    await review.locator('svg').first().screenshot({path:path.join(destination,'native-preview.png')});
    const report={status:'exported',events:result.events,mathErrors:errors,mathContainers:math,
                  svgBytes:Buffer.byteLength(svg),source:path.basename(source)};
    fs.writeFileSync(path.join(destination,'native-export-QA.json'),JSON.stringify(report,null,2)+'\n');
    if(errors)throw new Error(`${errors} native math errors`);
    console.log(JSON.stringify(report,null,2));
  } finally {
    if(browser)await browser.close();
    await new Promise(resolve=>server.close(resolve));
  }
}
main().catch(e=>{console.error(e);process.exitCode=1});
