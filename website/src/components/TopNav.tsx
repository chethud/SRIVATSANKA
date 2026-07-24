import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Bell, Layers, Menu, Moon, Plus, Search, Sun } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { useCreateAction } from '../context/CreateActionContext';
import { useLayout } from '../context/LayoutContext';
import { usePageSearchSlot } from '../context/PageSearchContext';
import { useTheme } from '../context/ThemeContext';
import type { Notification } from '../api/client';
import {
  getCreateActionForPath,
  getCreateButtonLabel,
  getSecondaryCreateActionForPath,
  getSecondaryCreateButtonLabel,
} from '../utils/createAction';
import { getUnreadNotifications } from '../utils/dashboardData';
import { getNotificationHref } from '../utils/notificationLink';
import { getTopNavTitle } from '../utils/topNavTitle';

export function TopNav() {
  const { notifications, stats, enquiries, markNotificationsRead } = useAppData();
  const { theme, toggleTheme } = useTheme();
  const { triggerCreate } = useCreateAction();
  const { isMobileNav, mobileNavOpen, toggleMobileNav } = useLayout();
  const { config: pageSearch } = usePageSearchSlot();
  const location = useLocation();
  const navigate = useNavigate();
  const [notifOpen, setNotifOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  const unread = getUnreadNotifications(notifications);
  const unreadCount = stats?.unread_notifications ?? 0;
  const pageAction = getCreateActionForPath(location.pathname);
  const secondaryAction = getSecondaryCreateActionForPath(location.pathname);
  const createLabel = getCreateButtonLabel(location.pathname);
  const secondaryLabel = getSecondaryCreateButtonLabel(secondaryAction);
  const pageTitle = !pageSearch ? getTopNavTitle(location.pathname) : null;

  function toggleNotifications() {
    setNotifOpen((open) => !open);
  }

  function handleNotificationClick(notification: Notification) {
    void markNotificationsRead([notification.id]);
    setNotifOpen(false);
    navigate(getNotificationHref(notification, enquiries));
  }

  useEffect(() => {
    if (!notifOpen) return;
    function onPointerDown(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
    }
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [notifOpen]);

  useEffect(() => {
    if (!notifOpen) return;

    const { overflow, paddingRight } = document.body.style;
    const scrollbarGap = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = 'hidden';
    if (scrollbarGap > 0) {
      document.body.style.paddingRight = `${scrollbarGap}px`;
    }

    function stopPageScroll(e: WheelEvent | TouchEvent) {
      const panel = notifRef.current?.querySelector('.topnav__panel');
      if (panel && panel.contains(e.target as Node)) return;
      e.preventDefault();
    }

    document.addEventListener('wheel', stopPageScroll, { passive: false });
    document.addEventListener('touchmove', stopPageScroll, { passive: false });

    return () => {
      document.body.style.overflow = overflow;
      document.body.style.paddingRight = paddingRight;
      document.removeEventListener('wheel', stopPageScroll);
      document.removeEventListener('touchmove', stopPageScroll);
    };
  }, [notifOpen]);

  function handleCreate(action: typeof pageAction | typeof secondaryAction) {
    setNotifOpen(false);
    if (!action) return;
    triggerCreate(action);
    requestAnimationFrame(() => {
      const id = action === 'session' ? 'page-add-session' : 'page-create-form';
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  return (
    <header className="topnav sticky top-0 z-30 mb-4 sm:mb-5">
      <div className="topnav__bar">
        <div className="topnav__leading">
          {isMobileNav && (
            <button
              type="button"
              onClick={toggleMobileNav}
              className="topnav__icon-btn topnav__menu-btn"
              aria-label={mobileNavOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileNavOpen}
            >
              <Menu size={18} />
            </button>
          )}
          {pageSearch ? (
            <div className="topnav__search">
              <Search size={16} className="topnav__search-icon" aria-hidden />
              <input
                type="search"
                value={pageSearch.value}
                onChange={(e) => pageSearch.onChange(e.target.value)}
                placeholder={pageSearch.placeholder}
                className="topnav__search-input"
                aria-label={pageSearch.placeholder}
              />
            </div>
          ) : (
            <div className="topnav__title-wrap">
              {pageTitle ? <p className="topnav__title">{pageTitle}</p> : <span />}
            </div>
          )}
        </div>

        <div className="topnav__actions">
          {secondaryAction && (
            <button
              type="button"
              onClick={() => handleCreate(secondaryAction)}
              className="topnav__btn topnav__btn--ghost"
            >
              <Layers size={16} />
              <span className="topnav__btn-label">{secondaryLabel}</span>
            </button>
          )}
          {pageAction && (
            <button
              type="button"
              onClick={() => handleCreate(pageAction)}
              className="topnav__btn topnav__btn--primary"
            >
              <Plus size={16} />
              <span className="topnav__btn-label">{createLabel}</span>
            </button>
          )}

          {(pageAction || secondaryAction) && <span className="topnav__divider" aria-hidden />}

          <button
            type="button"
            onClick={toggleTheme}
            className="topnav__icon-btn"
            aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
            title={theme === 'light' ? 'Dark mode' : 'Light mode'}
          >
            {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
          </button>

          <div className="relative" ref={notifRef}>
            <button
              type="button"
              onClick={toggleNotifications}
              className={`topnav__icon-btn ${notifOpen ? 'topnav__icon-btn--active' : ''}`}
              aria-label="Notifications"
              aria-expanded={notifOpen}
            >
              <Bell size={16} />
              {unreadCount > 0 && (
                <span className="topnav__badge">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>
            {notifOpen && (
              <div className="topnav__panel">
                <p className="topnav__panel-title">Notifications</p>
                {unread.length === 0 ? (
                  <p className="topnav__panel-empty">No new notifications</p>
                ) : (
                  unread.map((n) => (
                    <button
                      key={n.id}
                      type="button"
                      onClick={() => handleNotificationClick(n)}
                      className="topnav__panel-item topnav__panel-item--action"
                    >
                      <p className="font-medium text-[var(--foreground)]">{n.title}</p>
                      <p className="text-xs text-[var(--muted)] mt-0.5 line-clamp-2">{n.message}</p>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
