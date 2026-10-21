// Independent synthetic cases. Run: node --test independent_r5.mjs
// REVEAL_SOURCE can name the exact-SHA revealText.ts being audited.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
const source=process.env.REVEAL_SOURCE ?? 'C:/Users/p_pie/AppData/Local/Temp/lynx-codex-audit-20261019/frontend/src/screens/revealText.ts';
const {segments,finalText,toggleReveal}=await import(pathToFileURL(source));
test('UTF-16 prefix, tab/newline and two adjacent independent occurrences',()=>{
 const base='😀\r\nOSOBA_002\tOSOBA_002OSOBA_003.';
 const map={OSOBA_002:'Żaneta',OSOBA_003:'Anna Maria'};
 // Adjacent second token has no word boundary: preserve pre-existing TOKEN_RE semantics.
 const at=base.indexOf('OSOBA_002');
 const r=toggleReveal(new Set(),at,'OSOBA_002',map);
 assert.equal(finalText(base,map,r),'😀\r\nŻaneta\tOSOBA_002OSOBA_003.');
 assert.equal(finalText(base,map,toggleReveal(r,at,'OSOBA_002',map)),base);
});
test('two distinct tokens with the same original stay independent',()=>{
 const base='OSOBA_002 / OSOBA_003';
 const map={OSOBA_002:'Żaneta',OSOBA_003:'Żaneta'};
 const r=toggleReveal(new Set(),base.indexOf('OSOBA_003'),'OSOBA_003',map);
 assert.equal(finalText(base,map,r),'OSOBA_002 / Żaneta');
});
test('longer first original does not shift the second baseline occurrence',()=>{
 const base='OSOBA_002; OSOBA_003!';
 const map={OSOBA_002:'Anna Maria Kowalska',OSOBA_003:'Żaneta'};
 let r=toggleReveal(new Set(),0,'OSOBA_002',map);
 r=toggleReveal(r,base.indexOf('OSOBA_003'),'OSOBA_003',map);
 assert.equal(finalText(base,map,r),'Anna Maria Kowalska; Żaneta!');
 assert.equal(segments(base,map,r).filter(s=>s.revealed).length,2);
});
