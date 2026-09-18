import {
  AppBridge,
  PostMessageTransport,
} from "@modelcontextprotocol/ext-apps/app-bridge";
window.mountStories = async (html, result) => {
  const frame = document.createElement("iframe");
  frame.id = "app";
  frame.sandbox = "allow-scripts allow-downloads";
  frame.style = "width:100%;height:850px;border:0";
  document.body.replaceChildren(frame);
  const bridge = new AppBridge(
    null,
    { name: "Independent standards host", version: "1.0.0" },
    { serverTools: {}, serverResources: {}, updateModelContext: {} },
    { hostContext: { theme: "light", displayMode: "inline" } },
  );
  bridge.oncalltool = (args) => window.hostCall(args);
  bridge.onreadresource = (args) => window.hostRead(args);
  bridge.onupdatemodelcontext = async (args) => {
    window.savedContext = args;
    return {};
  };
  bridge.oninitialized = async () => {
    await bridge.sendToolInput({
      arguments: { story_id: result.structuredContent.story_id },
    });
    await bridge.sendToolResult(result);
  };
  await bridge.connect(
    new PostMessageTransport(frame.contentWindow, frame.contentWindow),
  );
  frame.srcdoc = html;
  window.storiesBridge = bridge;
};
