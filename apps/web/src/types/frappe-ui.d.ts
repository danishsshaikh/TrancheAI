declare module "frappe-ui" {
  import type { App, Component } from "vue";

  export const FrappeUI: { install(app: App): void };
  export const Badge: Component;
  export const Button: Component;
  export const Dialog: Component;
  export const Dropdown: Component;
  export const FormControl: Component;
}
