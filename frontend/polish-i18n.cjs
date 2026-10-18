const fs=require('fs');let p='src/App.tsx',s=fs.readFileSync(p,'utf8');
s=s.replace('<LanguageSelect/>','<LanguageSelect disabled={!!window.pywebview?.api && !bootstrap}/>');
s=s.replace('title: t("Update and restart?"), text: t("The app will download the update, verify its checksum, and restart. Your API key and saved data will be preserved.")','title: "Update and restart?", text: "The app will download the update, verify its checksum, and restart. Your API key and saved data will be preserved."');
s=s.replace('notify({text: t("Imported {v0} keywords. Click Save keywords to keep them in the bot.", {v0: words.length})})','notify({text: "Imported {v0} keywords. Click Save keywords to keep them in the bot.", params: {v0: words.length}})');
s=s.replace('<th>Subscribers</th>','<th>{t("Subscribers")}</th>');
s=s.replace('t("AI Automation&#10;AI Agent&#10;AI video creation")','t("AI Automation\\nAI Agent\\nAI video creation")');fs.writeFileSync(p,s);
for(const p of ['src/components/ConfirmDialog.tsx','src/components/ResultDetails.tsx','src/components/TableLoading.tsx','src/components/WorkspaceHeading.tsx','src/components/KeywordTable.tsx']){let s=fs.readFileSync(p,'utf8').replace('const { t, locale } = useI18n();','const { t } = useI18n();');fs.writeFileSync(p,s);}
// Avoid translated notices being frozen in the language used at click time.
p='src/components/ContactComposer.tsx';s=fs.readFileSync(p,'utf8');for(const key of ['Contact draft saved in the bot.','Message copied. You can paste it into the conversation.','Contact opened. Send your message on that platform.'])s=s.replace('notify({text: t('+JSON.stringify(key)+')})','notify({text: '+JSON.stringify(key)+'})');fs.writeFileSync(p,s);
