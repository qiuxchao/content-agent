"use client";

import { ConfigProvider, App } from "antd";
import zhCN from "antd/locale/zh_CN";

export function AntdProvider({ children }: { children: React.ReactNode }) {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: "#c47a2a",
          colorSuccess: "#5a8a5e",
          colorError: "#c25a4a",
          colorInfo: "#5a7a9a",
          borderRadius: 10,
          fontFamily: "var(--font-geist-sans), 'Helvetica Neue', Arial, sans-serif",
          colorBgContainer: "#faf8f5",
          colorBorder: "#e8e2d9",
          colorText: "#2c2420",
          colorTextSecondary: "#8c7e6f",
          controlHeight: 40,
        },
        components: {
          Button: {
            primaryShadow: "0 2px 8px rgba(196, 122, 42, 0.25)",
            borderRadius: 10,
          },
          Input: {
            activeBorderColor: "#c47a2a",
            hoverBorderColor: "#c4bbb0",
          },
          Tag: {
            borderRadiusSM: 6,
          },
          Steps: {
            iconSize: 28,
          },
          Progress: {
            remainingColor: "#e8e2d9",
          },
        },
      }}
    >
      <App>{children}</App>
    </ConfigProvider>
  );
}
