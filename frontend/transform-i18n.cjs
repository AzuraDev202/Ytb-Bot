const ts=require('typescript'),fs=require('fs');
const catalog=JSON.parse(fs.readFileSync('src/vi.generated.json','utf8'));
const excluded=new Set(['Channel Name','Search Keyword','Total Views','Channel Age (Days)','Other Contacts','Channel URL','AI technology','AI Automation\nAI Agent\nAI video creation']);
const paths=['src/App.tsx',...fs.readdirSync('src/components').filter(x=>x.endsWith('.tsx')).map(x=>'src/components/'+x)];
for(const p of paths){let source=fs.readFileSync(p,'utf8');const sf=ts.createSourceFile(p,source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX),edits=[];
function edit(n,value){edits.push([n.getStart(sf),n.end,value]);}
function inJsx(n){for(let x=n.parent;x;x=x.parent){if(ts.isJsxExpression(x)||ts.isJsxAttribute(x))return true;if(ts.isFunctionDeclaration(x))return false;}return false;}
function visit(n){
 if(ts.isJsxText(n)&&catalog[n.text.trim()]){const raw=n.getText(sf),trimmed=raw.trim();edit(n,raw.slice(0,raw.indexOf(trimmed))+'{t('+JSON.stringify(trimmed)+')}'+raw.slice(raw.indexOf(trimmed)+trimmed.length));return;}
 if(ts.isTemplateExpression(n)&&inJsx(n)){let key=n.head.text;const params=[];n.templateSpans.forEach((s,i)=>{key+='{v'+i+'}'+s.literal.text;params.push('v'+i+': '+s.expression.getText(sf));});if(/[A-Za-z]{3}/.test(key)&&!key.includes('input[')){catalog[key]=key;edit(n,'t('+JSON.stringify(key)+', {'+params.join(', ')+'})');return;}}
 if((ts.isStringLiteral(n)||ts.isNoSubstitutionTemplateLiteral(n))&&catalog[n.text]&&!excluded.has(n.text)&&inJsx(n)&&!ts.isElementAccessExpression(n.parent)){
 const wrapped='t('+JSON.stringify(n.text)+')';edit(n,ts.isJsxAttribute(n.parent)?'{'+wrapped+'}':wrapped);return;}
 ts.forEachChild(n,visit);
}
visit(sf);edits.sort((a,b)=>b[0]-a[0]).forEach(([start,end,value])=>source=source.slice(0,start)+value+source.slice(end));
source="import { useI18n } from '"+(p==='src/App.tsx'?'./i18n':'../i18n')+"';\n"+source;
source=source.replace(/(export (?:default )?function \w+[\s\S]*?\) \{)/, '$1\n  const { t, locale } = useI18n();');
fs.writeFileSync(p,source);
}
fs.writeFileSync('src/vi.generated.json',JSON.stringify(catalog,null,2));
