import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { I18nProvider } from './i18n';
import { InteractionFeedback } from './components/InteractionFeedback';
import './styles.css';
import './studio.css';
createRoot(document.getElementById('root')!).render(<React.StrictMode><I18nProvider><App /><InteractionFeedback/></I18nProvider></React.StrictMode>);
