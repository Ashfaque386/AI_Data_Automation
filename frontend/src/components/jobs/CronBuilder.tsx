import React, { useState, useEffect } from 'react';
import { jobsApi } from '../../services/jobsApi';
import './CronBuilder.css';

interface CronBuilderProps {
    value: string;
    onChange: (cron: string) => void;
}

interface CronPreset {
    name: string;
    value: string;
}

export const CronBuilder: React.FC<CronBuilderProps> = ({ value, onChange }) => {
    const [mode, setMode] = useState<'preset' | 'custom'>('preset');
    const [selectedPreset, setSelectedPreset] = useState('');

    // Custom mode fields
    const [minute, setMinute] = useState('0');
    const [hour, setHour] = useState('0');
    const [dayOfMonth, setDayOfMonth] = useState('*');
    const [month, setMonth] = useState('*');
    const [selectedDays, setSelectedDays] = useState<number[]>([]);

    // Preview
    const [nextRuns, setNextRuns] = useState<string[]>([]);
    const [validationError, setValidationError] = useState<string | null>(null);

    const presets: CronPreset[] = [
        { name: 'Every 5 minutes', value: '*/5 * * * *' },
        { name: 'Every 15 minutes', value: '*/15 * * * *' },
        { name: 'Every 30 minutes', value: '*/30 * * * *' },
        { name: 'Hourly', value: '0 * * * *' },
        { name: 'Daily at midnight', value: '0 0 * * *' },
        { name: 'Daily at 2 AM', value: '0 2 * * *' },
        { name: 'Daily at 6 AM', value: '0 6 * * *' },
        { name: 'Daily at noon', value: '0 12 * * *' },
        { name: 'Weekly (Sunday midnight)', value: '0 0 * * 0' },
        { name: 'Weekly (Monday midnight)', value: '0 0 * * 1' },
        { name: 'Monthly (1st at midnight)', value: '0 0 1 * *' },
    ];

    const daysOfWeek = [
        { label: 'Sun', value: 0 },
        { label: 'Mon', value: 1 },
        { label: 'Tue', value: 2 },
        { label: 'Wed', value: 3 },
        { label: 'Thu', value: 4 },
        { label: 'Fri', value: 5 },
        { label: 'Sat', value: 6 },
    ];

    // Parse incoming value to set initial state
    useEffect(() => {
        if (value) {
            const preset = presets.find(p => p.value === value);
            if (preset) {
                setMode('preset');
                setSelectedPreset(value);
            } else {
                setMode('custom');
                parseCronExpression(value);
            }
        }
    }, []);

    const parseCronExpression = (cron: string) => {
        const parts = cron.split(' ');
        if (parts.length === 5) {
            setMinute(parts[0]);
            setHour(parts[1]);
            setDayOfMonth(parts[2]);
            setMonth(parts[3]);

            // Parse day of week
            if (parts[4] !== '*') {
                const days = parts[4].split(',').map(d => parseInt(d));
                setSelectedDays(days);
            }
        }
    };

    const buildCronExpression = (): string => {
        const dayOfWeek = selectedDays.length > 0
            ? selectedDays.sort().join(',')
            : '*';

        return `${minute} ${hour} ${dayOfMonth} ${month} ${dayOfWeek}`;
    };

    const handlePresetChange = (presetValue: string) => {
        setSelectedPreset(presetValue);
        onChange(presetValue);
        validateAndPreview(presetValue);
    };

    const handleCustomChange = () => {
        const cron = buildCronExpression();
        onChange(cron);
        validateAndPreview(cron);
    };

    useEffect(() => {
        if (mode === 'custom') {
            handleCustomChange();
        }
    }, [minute, hour, dayOfMonth, month, selectedDays]);

    const validateAndPreview = async (cron: string) => {
        if (!cron || cron.trim() === '') {
            setNextRuns([]);
            setValidationError(null);
            return;
        }

        try {
            const response = await jobsApi.validateCron(cron);
            if (response.valid) {
                setNextRuns(response.next_runs || []);
                setValidationError(null);
            } else {
                setNextRuns([]);
                setValidationError(response.error || 'Invalid cron expression');
            }
        } catch (err) {
            console.error('Validation failed:', err);
            setValidationError('Failed to validate cron expression');
        }
    };

    const toggleDay = (day: number) => {
        if (selectedDays.includes(day)) {
            setSelectedDays(selectedDays.filter(d => d !== day));
        } else {
            setSelectedDays([...selectedDays, day]);
        }
    };

    const formatNextRun = (isoString: string) => {
        const date = new Date(isoString);
        return date.toLocaleString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    return (
        <div className="cron-builder">
            <div className="cron-mode-selector">
                <button
                    type="button"
                    className={`mode-btn ${mode === 'preset' ? 'active' : ''}`}
                    onClick={() => setMode('preset')}
                >
                    📋 Use Preset
                </button>
                <button
                    type="button"
                    className={`mode-btn ${mode === 'custom' ? 'active' : ''}`}
                    onClick={() => setMode('custom')}
                >
                    ⚙️ Custom Schedule
                </button>
            </div>

            {mode === 'preset' ? (
                <div className="preset-mode">
                    <label>Select Schedule Template</label>
                    <select
                        value={selectedPreset}
                        onChange={(e) => handlePresetChange(e.target.value)}
                        className="preset-select"
                    >
                        <option value="">Choose a preset...</option>
                        {presets.map((preset) => (
                            <option key={preset.value} value={preset.value}>
                                {preset.name}
                            </option>
                        ))}
                    </select>
                </div>
            ) : (
                <div className="custom-mode">
                    <div className="cron-fields">
                        <div className="field-group">
                            <label>Minute (0-59)</label>
                            <input
                                type="text"
                                value={minute}
                                onChange={(e) => setMinute(e.target.value)}
                                placeholder="0"
                            />
                            <small>Use * for every minute, */5 for every 5 minutes</small>
                        </div>

                        <div className="field-group">
                            <label>Hour (0-23)</label>
                            <input
                                type="text"
                                value={hour}
                                onChange={(e) => setHour(e.target.value)}
                                placeholder="0"
                            />
                            <small>Use * for every hour, */2 for every 2 hours</small>
                        </div>

                        <div className="field-group">
                            <label>Day of Month (1-31)</label>
                            <input
                                type="text"
                                value={dayOfMonth}
                                onChange={(e) => setDayOfMonth(e.target.value)}
                                placeholder="*"
                            />
                            <small>Use * for every day</small>
                        </div>

                        <div className="field-group">
                            <label>Month (1-12)</label>
                            <input
                                type="text"
                                value={month}
                                onChange={(e) => setMonth(e.target.value)}
                                placeholder="*"
                            />
                            <small>Use * for every month</small>
                        </div>

                        <div className="field-group days-of-week">
                            <label>Days of Week</label>
                            <div className="day-checkboxes">
                                {daysOfWeek.map((day) => (
                                    <label key={day.value} className="day-checkbox">
                                        <input
                                            type="checkbox"
                                            checked={selectedDays.includes(day.value)}
                                            onChange={() => toggleDay(day.value)}
                                        />
                                        <span>{day.label}</span>
                                    </label>
                                ))}
                            </div>
                            <small>Leave all unchecked for every day</small>
                        </div>
                    </div>
                </div>
            )}

            <div className="cron-expression-display">
                <label>Cron Expression:</label>
                <code>{mode === 'preset' ? selectedPreset : buildCronExpression()}</code>
            </div>

            {validationError && (
                <div className="cron-error">
                    ⚠️ {validationError}
                </div>
            )}

            {nextRuns.length > 0 && (
                <div className="next-runs-preview">
                    <label>Next 5 Runs:</label>
                    <ul>
                        {nextRuns.map((run, index) => (
                            <li key={index}>
                                <span className="run-icon">▶</span>
                                {formatNextRun(run)}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};
