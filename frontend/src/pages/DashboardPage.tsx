import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Activity, Users, TrendingUp, Clock } from "lucide-react";

export function DashboardPage() {
  // Mock data for demonstration
  const kpis = [
    {
      title: "Total Searches",
      value: "1,234",
      change: "+12.5%",
      icon: Activity,
      color: "text-blue-500",
    },
    {
      title: "Recipe Transformations",
      value: "456",
      change: "+8.2%",
      icon: TrendingUp,
      color: "text-green-500",
    },
    {
      title: "Active Users",
      value: "89",
      change: "+23.1%",
      icon: Users,
      color: "text-purple-500",
    },
    {
      title: "Average Response Time",
      value: "1.2s",
      change: "-5.3%",
      icon: Clock,
      color: "text-orange-500",
    },
  ];

  return (
    <div className="p-8">
      <div className="mx-auto max-w-7xl space-y-8">
        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {kpis.map((kpi, index) => (
            <Card key={index}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {kpi.title}
                </CardTitle>
                <kpi.icon className={cn("h-4 w-4", kpi.color)} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{kpi.value}</div>
                <p className="text-xs text-muted-foreground">
                  <span
                    className={
                      kpi.change.startsWith("+")
                        ? "text-green-500"
                        : "text-red-500"
                    }
                  >
                    {kpi.change}
                  </span>{" "}
                  compared to last week
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Main Content Area */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
          {/* Overview Chart */}
          <Card className="col-span-4">
            <CardHeader>
              <CardTitle>Overview</CardTitle>
              <CardDescription>Usage analytics and statistics</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px] flex items-center justify-center">
              <div className="text-center text-muted-foreground">
                <Activity className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p>Graph visualization will be displayed here</p>
                <p className="text-sm mt-2">
                  Connect to the analytics service to see real data
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card className="col-span-3">
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Latest user interactions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[1, 2, 3, 4].map((item) => (
                  <div key={item} className="flex items-center gap-4">
                    <div className="h-2 w-2 rounded-full bg-primary" />
                    <div className="flex-1">
                      <p className="text-sm font-medium">Activity {item}</p>
                      <p className="text-xs text-muted-foreground">
                        {item} minute{item > 1 ? "s" : ""} ago
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Additional Information */}
        <Card>
          <CardHeader>
            <CardTitle>Popular Recipes</CardTitle>
            <CardDescription>
              Most searched and transformed recipes
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-center text-muted-foreground py-8">
              <TrendingUp className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p>Popular recipes will be displayed here</p>
              <p className="text-sm mt-2">
                Data will be loaded from the analytics service
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Add cn utility import at top
import { cn } from "@/lib/utils";
