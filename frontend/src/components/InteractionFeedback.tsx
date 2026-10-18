import { useEffect } from 'react';

/** Acknowledges clicks without intercepting controls or repeating their actions. */
export function InteractionFeedback() {
  useEffect(() => {
    const effects = new Set<HTMLSpanElement>();
    function acknowledge(event: MouseEvent) {
      if (document.documentElement.dataset.motion === 'off' || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      const target = event.target instanceof Element ? event.target.closest<HTMLButtonElement>('button.button, button.icon-button, button.nav-item, .preset-row button') : null;
      if (!target || target.disabled || target.getAttribute('aria-disabled') === 'true') return;
      // Top-layer dialogs need their feedback in the same top layer.
      const host = target.closest('dialog') || document.body;
      const bounds = target.getBoundingClientRect();
      const effect = document.createElement('span');
      effect.className = 'click-feedback';
      effect.setAttribute('aria-hidden', 'true');
      const x = event.detail ? event.clientX : bounds.left + bounds.width / 2;
      const y = event.detail ? event.clientY : bounds.top + bounds.height / 2;
      effect.style.left = `${x - 18}px`;
      effect.style.top = `${y - 18}px`;
      if (effects.size >= 6) {
        const oldest = effects.values().next().value;
        oldest?.remove();
        if (oldest) effects.delete(oldest);
      }
      host.append(effect);
      effects.add(effect);
      const animation = effect.animate([
        {transform: 'scale(.4)', opacity: .65},
        {transform: 'scale(1.4)', opacity: 0},
      ], {duration: 320, easing: 'cubic-bezier(.16, 1, .3, 1)'});
      void animation.finished.catch(() => {}).finally(() => {effect.remove(); effects.delete(effect);});
    }
    document.addEventListener('click', acknowledge, true);
    return () => {
      document.removeEventListener('click', acknowledge, true);
      effects.forEach(effect => {effect.getAnimations().forEach(animation => animation.cancel()); effect.remove();});
    };
  }, []);
  return null;
}
