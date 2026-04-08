'use client';

import { useState } from 'react';
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

export default function Settings() {
  const [settings, setSettings] = useState({
    systemName: 'Network Traffic Monitor',
    refreshInterval: '30',
    alertThreshold: '80',
    anomalyDetection: true,
    emailAlerts: true,
    slackNotifications: false,
    theme: 'dark',
  });

  const handleSave = () => {
    // In a real app, this would save to backend
    console.log('Settings saved:', settings);
  };

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
                value={settings.systemName}
                onChange={(e) =>
                  setSettings({ ...settings, systemName: e.target.value })
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
                value={settings.refreshInterval}
                onChange={(e) =>
                  setSettings({ ...settings, refreshInterval: e.target.value })
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
                value={settings.alertThreshold}
                onChange={(e) =>
                  setSettings({ ...settings, alertThreshold: e.target.value })
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
                checked={settings.anomalyDetection}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, anomalyDetection: checked })
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
                checked={settings.emailAlerts}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, emailAlerts: checked })
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
                checked={settings.slackNotifications}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, slackNotifications: checked })
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
            >
              Retrain Model
            </Button>
          </CardContent>
        </Card>

        {/* Save Button */}
        <div className="flex justify-end">
          <Button
            size="lg"
            onClick={handleSave}
            className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <Save className="h-4 w-4" />
            Save Settings
          </Button>
        </div>
      </div>
    </DashboardLayout>
  );
}
