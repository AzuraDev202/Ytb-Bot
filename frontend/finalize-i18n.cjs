const fs=require('fs');
for(const p of ['src/App.tsx',...fs.readdirSync('src/components').filter(x=>x.endsWith('.tsx')).map(x=>'src/components/'+x)]){
 let s=fs.readFileSync(p,'utf8');
 s=s.replaceAll("'en-US'",'locale');
 s=s.replace(/const format = \(value: number\) => new Intl.NumberFormat\(locale\).format\(value\);\r?\n/,'');
 if(['src/App.tsx','src/components/WorkbookView.tsx'].includes(p))s=s.replace('const { t, locale } = useI18n();','const { t, locale } = useI18n();\n  const format = (value: number) => new Intl.NumberFormat(locale).format(value);');
 s=s.replaceAll('setTab(t("keywords"))',"setTab('keywords')").replaceAll('tab === t("keywords")',"tab === 'keywords'");
 s=s.replaceAll('htmlFor={t("keywords")}','htmlFor="keywords"').replaceAll('id={t("keywords")}','id="keywords"');
 for(const expr of ['content.label','content.title','statuses[status]','statuses[state.status]','item.label','statusLabels[item.status] || item.status','labels[item.status] || item.status','labels[run.status] || run.status','notice.text','errors.key','errors.age','errors.views','request?.title','request?.text','failure','label'])s=s.replaceAll('{'+expr+'}','{t('+expr+(expr.includes('?.')?" || ''":'')+')}');
 s=s.replace('{errors.keywords || t(', '{errors.keywords ? t(errors.keywords) : t(');
 s=s.replace('<span>views</span>','<span>{t("views")}</span>').replace('>YouTube API Key <','>{t("YouTube API Key")} <');
 s=s.replace('>CREATOR WORKSPACE<','>{t("CREATOR WORKSPACE")}<').replace('>Studio<','>{t("Studio")}<').replace('>Desktop<','>{t("Desktop")}<');
 s=s.replace('>Sheet<select','>{t("Sheet")}<select').replace("'BOT DATA' : 'LOCAL FILE'","t('BOT DATA') : t('LOCAL FILE')");
 s=s.replace('>{meta.filename}<',">{readOnly && meta.internal ? meta.filename.replace(/^Scan(?= #)/, t('Scan')) : meta.filename}<");
 s=s.replace('{meta.sheets.length} sheet ·',"{meta.sheets.length} {t('Sheet')} ·");
 s=s.replace('<span>{label}</span>', '<span>{t(label)}</span>');
 fs.writeFileSync(p,s);
}
