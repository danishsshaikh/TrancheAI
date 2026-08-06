import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { demoProjects } from "../api/client";
import { Metric } from "../components/Metric";

const trancheSchema = z.object({
  projectCode: z.string().min(1),
  requestedAmount: z.coerce.number().nonnegative(),
  approvedAmount: z.coerce.number().nonnegative(),
  paymentReference: z.string().optional()
}).refine((value) => value.approvedAmount <= value.requestedAmount, {
  message: "Approved amount cannot exceed requested amount.",
  path: ["approvedAmount"]
});

type TrancheForm = z.infer<typeof trancheSchema>;

export function TrancheFormPage() {
  const project = demoProjects[0];
  const form = useForm<TrancheForm>({ resolver: zodResolver(trancheSchema), defaultValues: { projectCode: project.projectCode, requestedAmount: 0, approvedAmount: 0 } });
  return (
    <div className="max-w-4xl space-y-5">
      <div>
        <p className="text-sm text-muted">Tranches</p>
        <h1 className="text-2xl font-semibold">Create tranche</h1>
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Project" value={project.projectCode} />
        <Metric label="Total Sanctioned" value={project.summary.totalSanctionedAmount} />
        <Metric label="Net Disbursed" value={project.summary.netDisbursedAmount} />
        <Metric label="Available Balance" value={project.summary.availableSanctionedBalance} />
      </div>
      <form className="space-y-4 rounded-md border border-line bg-panel p-4">
        <label className="block text-sm font-medium">
          Project code
          <input className="focus-ring mt-1 w-full rounded-md border border-line bg-surface px-3 py-2" {...form.register("projectCode")} />
        </label>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block text-sm font-medium">
            Requested amount
            <input className="focus-ring mt-1 w-full rounded-md border border-line bg-surface px-3 py-2" type="number" {...form.register("requestedAmount")} />
          </label>
          <label className="block text-sm font-medium">
            Approved amount
            <input className="focus-ring mt-1 w-full rounded-md border border-line bg-surface px-3 py-2" type="number" {...form.register("approvedAmount")} />
            {form.formState.errors.approvedAmount ? <span className="mt-1 block text-sm text-danger">{form.formState.errors.approvedAmount.message}</span> : null}
          </label>
        </div>
        <label className="block text-sm font-medium">
          Payment reference
          <input className="focus-ring mt-1 w-full rounded-md border border-line bg-surface px-3 py-2" {...form.register("paymentReference")} />
        </label>
        <button className="focus-ring rounded-md bg-accent px-4 py-2 text-sm font-medium text-surface" type="button">Submit for review</button>
      </form>
    </div>
  );
}

