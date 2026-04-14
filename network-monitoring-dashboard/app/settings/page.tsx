'use client';

import { useEffect, useState } from 'react';
import { Save } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { DashboardLayout } from '@/components/dashboard-layout';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { getSettings, updateSettings, retrainModel } from '@/lib/api';

interface SettingsData {
  system_name: string;
  refresh_interval_seconds: number;
  alert_threshold_mbps: number;
  anomaly_detection: boolean;
  email_alerts: boolean;
  slack_notifications: boolean;
  theme: string;
}

export default function Settings() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isRetraining, setIsRetraining] = useState(false);

  useEffect(() => {
    async function fetchSettings() {
      try {
        const res = await getSettings();
        setSettings(res);
      } catch (error) {
        console.error('Failed to fetch settings:', error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchSettings();
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setIsSaving(true);
    try {
      await updateSettings({
        system_name: settings.system_name,
        refresh_interval_seconds: settings.refresh_interval_seconds,
        alert_threshold_mbps: settings.alert_threshold_mbps,
        anomaly_detection: settings.anomaly_detection,
        email_alerts: settings.email_alerts,
        slack_notifications: settings.slack_notifications,
        theme: settings.theme,
      });
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleRetrain = async () => {
    setIsRetraining(true);
    try {
      await retrainModel();
    } catch (error) {
      console.error('Failed to retrain model:', error);
    } finally {
      setIsRetraining(false);
    }
  };

  if (isLoading || !settings) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground">Loading...</div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-foreground mb-2">Settings</h1>
          <p className="text-muted-foreground">
            Configure dashboard preferences and system parameters
          </p>
        </div>

        {/* General Settings */}
        <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
          <CardHeader>
            <CardTitle>General Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 md:space-y-6">
            <div className="space-y-2">
              <Label htmlFor="systemName" className="text-foreground">
                System Name
              </Label>
              <Input
                id="systemName"
                value={settings.system_name}
                onChange={(e) =>
                  setSettings({ ...settings, system_name: e.target.value })
                }
                className="bg-input border-border text-foreground"
                placeholder="Enter system name"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="refreshInterval" className="text-foreground">
                Data Refresh Interval (seconds)
              </Label>
              <Input
                id="refreshInterval"
                type="number"
                value={settings.refresh_interval_seconds}
                onChange={(e) =>
                  setSettings({ ...settings, refresh_interval_seconds: parseInt(e.target.value) || 0 })
                }
                className="bg-input border-border text-foreground"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="alertThreshold" className="text-foreground">
                Alert Threshold (Mbps)
              </Label>
              <Input
                id="alertThreshold"
                type="number"
                value={settings.alert_threshold_mbps}
                onChange={(e) =>
                  setSettings({ ...settings, alert_threshold_mbps: parseInt(e.target.value) || 0 })
                }
                className="bg-input border-border text-foreground"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="theme" className="text-foreground">
                Theme
              </Label>
              <Select
                value={settings.theme}
                onValueChange={(value) =>
                  setSettings({ ...settings, theme: value })
                }
              >
                <SelectTrigger id="theme">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="dark">Dark</SelectItem>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="auto">Auto</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Feature Toggles */}
        <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
          <CardHeader>
            <CardTitle>Features & Notifications</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground font-semibold">
                  Anomaly Detection
                </Label>
                <p className="text-sm text-muted-foreground">
                  Enable AI-powered anomaly detection
                </p>
              </div>
              <Switch
                checked={settings.anomaly_detection}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, anomaly_detection: checked })
                }
              />
            </div>

            <div className="h-px bg-border" />

            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground font-semibold">
                  Email Alerts
                </Label>
                <p className="text-sm text-muted-foreground">
                  Receive alerts via email
                </p>
              </div>
              <Switch
                checked={settings.email_alerts}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, email_alerts: checked })
                }
              />
            </div>

            <div className="h-px bg-border" />

            <div className="flex items-center justify-between">
              <div>
                <Label className="text-foreground font-semibold">
                  Slack Notifications
                </Label>
                <p className="text-sm text-muted-foreground">
                  Send alerts to Slack channels
                </p>
              </div>
              <Switch
                checked={settings.slack_notifications}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, slack_notifications: checked })
                }
              />
            </div>
          </CardContent>
        </Card>

        {/* Model Settings */}
        <Card className="border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/40">
          <CardHeader>
            <CardTitle>AI Model Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-3 md:gap-4 md:grid-cols-2">
              <div>
                <h3 className="font-semibold text-foreground mb-2">
                  Current Model
                </h3>
                <p className="text-muted-foreground">LSTM v2.1</p>
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-2">
                  Last Training
                </h3>
                <p className="text-muted-foreground">2024-02-15</p>
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-2">
                  Training Data Points
                </h3>
                <p className="text-muted-foreground">8,640</p>
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-2">
                  Model Accuracy
                </h3>
                <p className="text-muted-foreground">94.8%</p>
              </div>
            </div>
            <Button
              variant="outline"
              className="w-full border-border text-foreground hover:bg-muted"
              onClick={handleRetrain}
              disabled={isRetraining}
            >
              {isRetraining ? 'Retraining...' : 'Retrain Model'}
            </Button>
          </CardContent>
        </Card>

        {/* Save Button */}
        <div className="flex justify-end">
          <Button
            size="lg"
            onClick={handleSave}
            disabled={isSaving}
            className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <Save className="h-4 w-4" />
            {isSaving ? 'Saving...' : 'Save Settings'}
          </Button>
        </div>
      </div>
    </DashboardLayout>
  );
}
