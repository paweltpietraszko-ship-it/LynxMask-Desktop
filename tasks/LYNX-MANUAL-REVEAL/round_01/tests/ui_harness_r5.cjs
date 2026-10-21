const fs = require('node:fs');
const path = require('node:path');
const front = 'C:/Users/p_pie/AppData/Local/Temp/lynx-codex-audit-20261019/frontend';
const esbuild = require(front + '/node_modules/esbuild');
const entry = `
import React from '${front}/node_modules/react/index.js';
import {createRoot} from '${front}/node_modules/react-dom/client.js';
import Screen from '${front}/src/screens/Pseudonimizuj.tsx';
const base = '[Kod sesji PSE-TEST]\\n01. OSOBA_033 zakwitła.\\n02. Pani OSOBA_033 odebrała dokument.\\n03. OSOBA_001 podpisała.';
let mode='normal';
const capture={};
const show=()=>document.getElementById('capture').textContent=JSON.stringify(capture,null,2);
Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>{capture.copy=text;show();}}});
window.auditEncrypt=async (cmd,args)=>{capture.encryptionInput=new TextDecoder().decode(Uint8Array.from(args.plaintext));show();return args.plaintext;};
window.fetch=async (url,opts={})=>{
 if(String(url).endsWith('/profile/add-entity')) return Response.json({ok:true,token_id:'OSOBA_034'});
 if(String(url).endsWith('/archive')) {const b=JSON.parse(opts.body);capture.archive=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(b.enc_blob),c=>c.charCodeAt(0))));show();return Response.json({ok:true});}
 if(!String(url).endsWith('/preview')) throw Error('Unexpected network request');
 return Response.json({blocked:mode==='blocked',error:null,pse_code:'PSE-TEST',anonymized_preview:base,original_text:'synthetic',
 tokens:mode==='missing'?[]:[{token:'OSOBA_033',original:'Róża',type:'OSOBA',label:'Osoba'},{token:'OSOBA_001',original:'Anna Malina',type:'OSOBA',label:'Osoba'}],
 total:2,has_sensitive:true,anonymizer_active:true,ocr:null,guard_reasons:mode==='blocked'?['synthetic block']:[],guard_values:[]});
};
createRoot(document.getElementById('root')).render(<><section style={{background:'#ffe',color:'#111',padding:8}}>AUDYT: prawdziwy komponent, atrapy API/IPC. {['normal','blocked','missing'].map(x=><button onClick={()=>mode=x} key={x}>Test {x}</button>)}<pre id="capture"/></section><div style={{height:1100}}><Screen apiToken="audit-only"/></div></>);
`;
fs.writeFileSync(path.join(__dirname,'entry.tsx'),entry);
esbuild.buildSync({entryPoints:[path.join(__dirname,'entry.tsx')],bundle:true,outfile:path.join(__dirname,'bundle.js'),
 jsx:'automatic',nodePaths:[front+'/node_modules'],alias:{'@tauri-apps/api/core':path.join(__dirname,'ipc.ts')},define:{'process.env.NODE_ENV':'"development"'}});
fs.writeFileSync(path.join(__dirname,'index.html'),'<meta charset="utf-8"><title>Audyt MANUAL-REVEAL</title><div id="root"></div><script src="bundle.js"></script>');
console.log('Built isolated exact-SHA component harness');
