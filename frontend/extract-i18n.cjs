const ts = require('typescript');
const fs = require('fs');
const cp = require('child_process');
const paths = ['src/App.tsx','src/api.ts',...fs.readdirSync('src/components').filter(x=>x.endsWith('.tsx')).map(x=>'src/components/'+x)];
const catalog = {};
for (const p of paths) {
 const current = fs.readFileSync(p,'utf8');
 const old = cp.execFileSync('git',['show','HEAD~1:frontend/'+p],{encoding:'utf8'});
 const collect = text => {const out=[]; const sf=ts.createSourceFile(p,text,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX); function visit(n){if(ts.isStringLiteral(n)||ts.isNoSubstitutionTemplateLiteral(n)||ts.isJsxText(n)||ts.isTemplateHead(n)||ts.isTemplateMiddle(n)||ts.isTemplateTail(n))out.push(n);ts.forEachChild(n,visit)} visit(sf);return out;};
 const a=collect(old), b=collect(current);
 if(a.length!==b.length) throw Error(p+' mismatched');
 a.forEach((n,i)=>{if(/[À-ỹ]/.test(n.text)){let key=b[i].text.trim(), value=n.text.trim(); if(key)catalog[key]=value;}});
}
fs.writeFileSync('src/vi.generated.json',JSON.stringify(catalog,null,2));

