const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('C:/Users/p_pie/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async () => {
  const browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe', headless:true});
  const page = await browser.newPage({viewport:{width:1100,height:850}});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  let blocked = false, archives = 0;
  await page.addInitScript(() => {
    let callback = 1;
    window.__TAURI_INTERNALS__ = {
      metadata:{currentWindow:{label:'main'},currentWebview:{label:'main'}},
      transformCallback:() => callback++,
      unregisterCallback:() => {},
      invoke:async (cmd) => {
        if (cmd === 'is_unlocked') return true;
        if (cmd === 'read_api_token') { await new Promise(r=>setTimeout(r,1200)); return 'synthetic-audit-token'; }
        if (cmd === 'encrypt_data') return [1,2,3,4];
        if (cmd.includes('listen')) return 1;
        return false;
      }
    };
    window.__TAURI_EVENT_PLUGIN_INTERNALS__ = {unregisterListener:() => {}};
  });
  await page.route('http://127.0.0.1:8765/**', async route => {
    const req = route.request(), url = new URL(req.url());
    let body = {ok:true};
    if (url.pathname === '/health') body = {status:'ok'};
    else if (url.pathname === '/version') body = {api:'audit',version:'audit'};
    else if (url.pathname === '/archive' && req.method() === 'GET') body = {documents:[]};
    else if (url.pathname === '/archive' && req.method() === 'POST') { archives++; body = {ok:true}; }
    else if (url.pathname === '/profile/entities') { await new Promise(r=>setTimeout(r,600)); body={entities:[]}; }
    else if (url.pathname === '/profile/guard-allowlist') { await new Promise(r=>setTimeout(r,600)); body={entries:[]}; }
    else if (url.pathname === '/preview') body = {pse_code:'PSE-2026-9001',anonymized_preview:'Kontakt: EMAIL_001',tokens:[{token:'EMAIL_001',original:'synthetic@example.org',type:'EMAIL',label:'Email'}],total:1,blocked,guard_reasons:blocked?['synthetic block']:[],error:null,anonymizer_active:true,original_text:'Kontakt: synthetic@example.org',ocr:null};
    await route.fulfill({status:200,contentType:'application/json',headers:{'access-control-allow-origin':'*','access-control-allow-headers':'*'},body:JSON.stringify(body)});
  });
  const screenshotDir = path.join(__dirname,'ui_r2');
  fs.mkdirSync(screenshotDir,{recursive:true});
  await page.goto('http://127.0.0.1:1437');
  await page.getByText('Ładowanie sesji…',{exact:true}).waitFor();
  await page.screenshot({path:path.join(screenshotDir,'loading.png'),fullPage:true});
  await page.getByPlaceholder(/Ctrl\+V/).waitFor();
  await page.locator('input[type=file]').first().setInputFiles({name:'synthetic.txt',mimeType:'text/plain',buffer:Buffer.from('Kontakt: synthetic@example.org')});
  await page.getByPlaceholder('Opis dokumentu (szyfrowany)...').fill('Audyt syntetyczny');
  const save = page.getByRole('button',{name:/Zapisz$/});
  assert.equal(await save.isEnabled(), true);
  await save.click();
  await page.waitForFunction(()=>document.body.innerText.includes('bibliotece'));
  assert.equal(archives,1);
  await page.screenshot({path:path.join(screenshotDir,'unblocked.png'),fullPage:true});
  blocked = true;
  await page.getByRole('button',{name:/Nowy dokument/}).click();
  await page.locator('input[type=file]').first().setInputFiles({name:'blocked.txt',mimeType:'text/plain',buffer:Buffer.from('Syntetyczny wynik zablokowany')});
  await page.getByPlaceholder('Opis dokumentu (szyfrowany)...').fill('Nie zapisuj zablokowanego');
  await page.waitForFunction(()=>Array.from(document.querySelectorAll('button')).some(b=>b.textContent.trim().endsWith('Zapisz') && b.disabled));
  assert.equal(await save.isDisabled(),true);
  await save.dispatchEvent('click');
  await page.getByPlaceholder('Opis dokumentu (szyfrowany)...').press('Enter');
  await page.waitForTimeout(100);
  assert.equal(archives,1);
  await page.screenshot({path:path.join(screenshotDir,'blocked.png'),fullPage:true});
  const theme = page.getByRole('button',{name:/Jasny motyw/});
  await theme.click();
  await page.getByRole('button',{name:/Ciemny motyw/}).waitFor();
  await page.screenshot({path:path.join(screenshotDir,'light.png'),fullPage:true});
  await page.getByRole('button',{name:/Ciemny motyw/}).click();
  await page.getByRole('button',{name:'Zabezpieczenia',exact:true}).click();
  const entities = page.getByRole('button',{name:'Pokaż encje',exact:true});
  await entities.click();
  assert.equal(await page.getByRole('button',{name:/Ładuję/}).isDisabled(),true);
  await page.getByRole('button',{name:'Odśwież listę',exact:true}).waitFor();
  const allowlist = page.getByRole('button',{name:'Pokaż wyjątki',exact:true});
  await allowlist.click();
  assert.equal(await page.getByRole('button',{name:/Ładuję/}).isDisabled(),true);
  await page.getByRole('button',{name:'Odśwież',exact:true}).waitFor();
  await page.screenshot({path:path.join(screenshotDir,'security.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({renderer:'PASS',saveUnblocked:1,saveBlocked:0,theme:'dark/light',loadingButtons:2,screenshots:screenshotDir}));
  await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});
