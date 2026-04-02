import React, { useState, useEffect } from 'react';
import './Settings.css';

const DEFAULT_SETTINGS = {
  id: null,
  notification_email: '',
  global_mode: 'approval',
  fit_score_threshold: 65,
  auto_apply_threshold: 75,
  target_roles: [],
  excluded_keywords: [],
  min_years_experience: 0,
  daily_digest_time: '08:00',
  scrape_interval_hours: 6,
};

const Settings = () => {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [tagInput, setTagInput] = useState({ target_roles: '', excluded_keywords: '' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      setSuccess(false);

      const response = await fetch('http://localhost:8000/settings/', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch settings: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();

      // Ensure all required fields exist with proper types
      setSettings({
        id: data?.id ?? null,
        notification_email: data?.notification_email ?? '',
        global_mode: data?.global_mode ?? 'approval',
        fit_score_threshold: Number(data?.fit_score_threshold) || 65,
        auto_apply_threshold: Number(data?.auto_apply_threshold) || 75,
        target_roles: Array.isArray(data?.target_roles) ? data.target_roles : [],
        excluded_keywords: Array.isArray(data?.excluded_keywords) ? data.excluded_keywords : [],
        min_years_experience: Number(data?.min_years_experience) || 0,
        daily_digest_time: data?.daily_digest_time ?? '08:00',
        scrape_interval_hours: Number(data?.scrape_interval_hours) || 6,
      });
    } catch (err) {
      setError(String(err?.message || 'An unknown error occurred'));
      console.error('Error fetching settings:', err);
      // Set default settings on error so form still renders
      setSettings(DEFAULT_SETTINGS);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleNumberChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({
      ...prev,
      [name]: value === '' ? 0 : Number(value),
    }));
  };

  const handleSliderChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({
      ...prev,
      [name]: Number(value),
    }));
  };

  const handleModeToggle = () => {
    setSettings(prev => ({
      ...prev,
      global_mode: prev.global_mode === 'approval' ? 'auto_apply' : 'approval',
    }));
  };

  const addTag = (field) => {
    const inputValue = tagInput[field]?.trim() || '';
    if (inputValue && !settings[field].includes(inputValue)) {
      setSettings(prev => ({
        ...prev,
        [field]: [...prev[field], inputValue],
      }));
      setTagInput(prev => ({
        ...prev,
        [field]: '',
      }));
    }
  };

  const removeTag = (field, index) => {
    setSettings(prev => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index),
    }));
  };

  const handleTagInputChange = (e, field) => {
    const { value } = e.target;
    setTagInput(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleTagKeyPress = (e, field) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag(field);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(false);

      if (!settings.id) {
        throw new Error('Settings ID not available');
      }

      const response = await fetch(`http://localhost:8000/settings/${settings.id}/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });

      if (!response.ok) {
        throw new Error(`Failed to save settings: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();

      // Ensure saved data has proper defaults
      setSettings({
        id: data?.id ?? settings.id,
        notification_email: data?.notification_email ?? settings.notification_email,
        global_mode: data?.global_mode ?? settings.global_mode,
        fit_score_threshold: Number(data?.fit_score_threshold) || settings.fit_score_threshold,
        auto_apply_threshold: Number(data?.auto_apply_threshold) || settings.auto_apply_threshold,
        target_roles: Array.isArray(data?.target_roles) ? data.target_roles : settings.target_roles,
        excluded_keywords: Array.isArray(data?.excluded_keywords) ? data.excluded_keywords : settings.excluded_keywords,
        min_years_experience: Number(data?.min_years_experience) || settings.min_years_experience,
        daily_digest_time: data?.daily_digest_time ?? settings.daily_digest_time,
        scrape_interval_hours: Number(data?.scrape_interval_hours) || settings.scrape_interval_hours,
      });

      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(String(err?.message || 'An unknown error occurred'));
      console.error('Error saving settings:', err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-container">
        <div className="loading">
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="settings-container">
      <div className="settings-header">
        <h1>Settings</h1>
        <p>Manage your AutoApply preferences and configuration</p>
      </div>

      {error && (
        <div className="alert alert-error">
          <span>Error: {error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {success && (
        <div className="alert alert-success">
          <span>Settings saved successfully!</span>
          <button onClick={() => setSuccess(false)}>×</button>
        </div>
      )}

      <div className="settings-form">
        {/* Notification Settings Section */}
        <section className="settings-section">
          <h2>Notification Settings</h2>
          <div className="form-group">
            <label htmlFor="notification_email">
              Email Address
              <span className="description">Where to send application updates and digests</span>
            </label>
            <input
              type="email"
              id="notification_email"
              name="notification_email"
              value={settings.notification_email || ''}
              onChange={handleInputChange}
              placeholder="your@email.com"
            />
          </div>

          <div className="form-group">
            <label htmlFor="daily_digest_time">
              Daily Digest Time
              <span className="description">Time to send daily job digest email</span>
            </label>
            <input
              type="time"
              id="daily_digest_time"
              name="daily_digest_time"
              value={settings.daily_digest_time || '08:00'}
              onChange={handleInputChange}
            />
          </div>
        </section>

        {/* Application Mode Section */}
        <section className="settings-section">
          <h2>Application Mode</h2>
          <div className="form-group">
            <label htmlFor="global_mode">
              Global Application Mode
              <span className="description">Choose how AutoApply handles job applications</span>
            </label>
            <div className="toggle-switch">
              <button
                type="button"
                className={`toggle-btn ${settings.global_mode === 'approval' ? 'active' : ''}`}
                onClick={handleModeToggle}
              >
                {settings.global_mode === 'approval' ? 'Approval Mode' : 'Auto Apply Mode'}
              </button>
              <span className="mode-indicator">
                {settings.global_mode === 'approval'
                  ? 'Review before applying'
                  : 'Apply automatically'}
              </span>
            </div>
          </div>
        </section>

        {/* Threshold Settings Section */}
        <section className="settings-section">
          <h2>Application Thresholds</h2>
          <div className="form-group">
            <label htmlFor="fit_score_threshold">
              Fit Score Threshold: <span className="threshold-value">{settings.fit_score_threshold}%</span>
              <span className="description">Minimum job fit score to consider (0-100)</span>
            </label>
            <input
              type="range"
              id="fit_score_threshold"
              name="fit_score_threshold"
              min="0"
              max="100"
              value={settings.fit_score_threshold || 65}
              onChange={handleSliderChange}
              className="slider"
            />
            <div className="slider-labels">
              <span>0%</span>
              <span>100%</span>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="auto_apply_threshold">
              Auto Apply Threshold: <span className="threshold-value">{settings.auto_apply_threshold}%</span>
              <span className="description">Minimum score to auto-apply without review (0-100)</span>
            </label>
            <input
              type="range"
              id="auto_apply_threshold"
              name="auto_apply_threshold"
              min="0"
              max="100"
              value={settings.auto_apply_threshold || 75}
              onChange={handleSliderChange}
              className="slider"
            />
            <div className="slider-labels">
              <span>0%</span>
              <span>100%</span>
            </div>
          </div>
        </section>

        {/* Job Criteria Section */}
        <section className="settings-section">
          <h2>Job Criteria</h2>
          <div className="form-group">
            <label htmlFor="min_years_experience">
              Minimum Years of Experience
              <span className="description">Minimum experience requirement for job targets</span>
            </label>
            <input
              type="number"
              id="min_years_experience"
              name="min_years_experience"
              value={settings.min_years_experience ?? 0}
              onChange={handleNumberChange}
              min="0"
            />
          </div>

          <div className="form-group">
            <label>
              Target Roles
              <span className="description">Job titles and roles to apply for (add multiple)</span>
            </label>
            <div className="tag-input-container">
              <input
                type="text"
                value={tagInput.target_roles || ''}
                onChange={(e) => handleTagInputChange(e, 'target_roles')}
                onKeyPress={(e) => handleTagKeyPress(e, 'target_roles')}
                placeholder="Type a role and press Enter"
              />
              <button
                type="button"
                onClick={() => addTag('target_roles')}
                className="add-tag-btn"
              >
                Add
              </button>
            </div>
            <div className="tags-container">
              {(settings.target_roles || []).map((role, index) => (
                <div key={index} className="tag">
                  <span>{role}</span>
                  <button
                    type="button"
                    onClick={() => removeTag('target_roles', index)}
                    className="remove-tag-btn"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>
              Excluded Keywords
              <span className="description">Keywords to avoid in job listings (add multiple)</span>
            </label>
            <div className="tag-input-container">
              <input
                type="text"
                value={tagInput.excluded_keywords || ''}
                onChange={(e) => handleTagInputChange(e, 'excluded_keywords')}
                onKeyPress={(e) => handleTagKeyPress(e, 'excluded_keywords')}
                placeholder="Type a keyword and press Enter"
              />
              <button
                type="button"
                onClick={() => addTag('excluded_keywords')}
                className="add-tag-btn"
              >
                Add
              </button>
            </div>
            <div className="tags-container">
              {(settings.excluded_keywords || []).map((keyword, index) => (
                <div key={index} className="tag tag-excluded">
                  <span>{keyword}</span>
                  <button
                    type="button"
                    onClick={() => removeTag('excluded_keywords', index)}
                    className="remove-tag-btn"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Scraping Settings Section */}
        <section className="settings-section">
          <h2>Scraping Settings</h2>
          <div className="form-group">
            <label htmlFor="scrape_interval_hours">
              Scrape Interval (Hours)
              <span className="description">How often to check for new job listings</span>
            </label>
            <input
              type="number"
              id="scrape_interval_hours"
              name="scrape_interval_hours"
              value={settings.scrape_interval_hours ?? 6}
              onChange={handleNumberChange}
              min="1"
              max="168"
            />
          </div>
        </section>

        {/* Action Buttons */}
        <div className="settings-actions">
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn btn-primary"
            type="button"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          <button
            onClick={fetchSettings}
            disabled={saving}
            className="btn btn-secondary"
            type="button"
          >
            Reload
          </button>
        </div>
      </div>
    </div>
  );
};

export default Settings;
