"use client";

import Link from "next/link";
import { BookOpen, LifeBuoy, Mail, MessageCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DashboardLayout } from "@/components/dashboard-layout";
import { pageSection, pageSubtitle, pageTitle } from "@/lib/ui-theme";

const resources = [
  {
    title: "Getting started",
    description:
      "Overview of the dashboard, simulation lab, and how live metrics refresh.",
    href: "/",
    icon: BookOpen,
  },
  {
    title: "Alerts & anomalies",
    description:
      "How severity levels map to network health and where to review detections.",
    href: "/alerts",
    icon: MessageCircle,
  },
];

export default function SupportPage() {
  return (
    <DashboardLayout breadcrumbs={[{ label: "Support" }]}>
      <div className="space-y-6">
        <div>
          <h1 className={pageTitle}>Support</h1>
          <p className={pageSubtitle}>
            Documentation and help for NetGuard network operations.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {resources.map((item) => {
            const Icon = item.icon;
            return (
              <Card key={item.href} className="h-full">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-gray-200 bg-gray-50 text-gray-600">
                      <Icon className="h-5 w-5" />
                    </div>
                    <CardTitle>{item.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-gray-600">{item.description}</p>
                  <Button
                    asChild
                    variant="outline"
                    className="border-gray-200 text-gray-900 hover:bg-gray-50"
                  >
                    <Link href={item.href}>Open</Link>
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className={pageSection}>
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-gray-200 bg-gray-50 text-gray-600">
              <LifeBuoy className="h-6 w-6" />
            </div>
            <div className="space-y-2">
              <h2 className="text-lg font-semibold text-gray-900">
                Need more help?
              </h2>
              <p className="text-sm text-gray-600">
                Contact your platform administrator or open an internal ticket for
                API, simulation, or GNN pipeline issues.
              </p>
              <a
                href="mailto:support@netguard.local"
                className="inline-flex items-center gap-2 text-sm font-medium text-gray-900 hover:text-gray-600"
              >
                <Mail className="h-4 w-4" />
                support@netguard.local
              </a>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
