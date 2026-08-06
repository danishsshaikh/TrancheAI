import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { createTranche, fetchProjects } from "../api/client";
import { useToken } from "../app/AuthContext";
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
  const token = useToken();
  const projects = useQuery({ queryKey: ["projects"], queryFn: () => fetchProjects(token) });
  const project = projects.data?.[0];
  const form = useForm<TrancheForm>({ resolver: zodResolver(trancheSchema), defaultValues: { projectCode: "", requestedAmount: 0, approvedAmount: 0 } });
  const mutation = useMutation({
    mutationFn: (values: TrancheForm) => {
      if (!project) throw new Error("No project selected.");
      return createTranche(token, project.id, {
        sequence_number: 1,
        transaction_type: "advance",
        requested_amount: String(values.requestedAmount),
        approved_amount: String(values.approvedAmount),
        payment_reference: values.paymentReference || undefined,
      });
    },
  });
  if (projects.isLoading) return <div className="rounded-md border border-line bg-panel p-8 text-sm text-muted">Loading projects.</div>;
  if (!project) return <div className="rounded-md border border-line bg-panel p-8 text-sm text-muted">Create a project before adding tranches.</div>;
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
      <form className="space-y-4 rounded-md border border-line bg-panel p-4" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <label className="block text-sm font-medium" htmlFor="projectCode">
          Project Code
          <input id="projectCode" className="focus-ring mt-1 w-full rounded-md border border-line bg-surface px-3 py-2" {...form.register("projectCode")} />
        </label>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block text-sm font-medium" htmlFor="requestedAmount">
            Requested Amount
            <input id="requestedAmount" className="focus-ring mt-1 w-full rounded-md border border-line bg-surface px-3 py-2" type="number" {...form.register("requestedAmount")} />
          </label>
          <label className="block text-sm font-medium" htmlFor="approvedAmount">
            Approved Amount
            <input id="approvedAmount" className="focus-ring mt-1 w-full rounded-md border border-line bg-surface px-3 py-2" type="number" {...form.register("approvedAmount")} />
            {form.formState.errors.approvedAmount ? <span className="mt-1 block text-sm text-danger">{form.formState.errors.approvedAmount.message}</span> : null}
          </label>
        </div>
        <label className="block text-sm font-medium" htmlFor="paymentReference">
          Payment Reference
          <input id="paymentReference" className="focus-ring mt-1 w-full rounded-md border border-line bg-surface px-3 py-2" {...form.register("paymentReference")} />
        </label>
        <button className="focus-ring rounded-md bg-accent px-4 py-2 text-sm font-medium text-surface" type="submit">Save Draft</button>
        {mutation.error ? <div className="text-sm text-danger">{mutation.error.message}</div> : null}
        {mutation.isSuccess ? <div className="text-sm text-accent">Draft tranche saved.</div> : null}
      </form>
    </div>
  );
}
