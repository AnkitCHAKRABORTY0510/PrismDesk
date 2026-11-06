import { useState, type FormEvent } from "react";

import { Alert, Button, Field, Input, Modal, Textarea } from "../../components/ui";
import { isoToLocalInput, localInputToIso } from "../../lib/format";
import { getErrorMessage } from "../../services/api";
import { createConference, updateConference, type Conference, type ImportantDate } from "../../services/conferenceService";

interface DateRow {
  label: string;
  date: string;
}

export default function ConferenceFormModal({
  open,
  conference,
  projectId,
  onClose,
  onSaved,
}: {
  open: boolean;
  conference?: Conference | null;
  projectId?: string;
  onClose: () => void;
  onSaved: (conference: Conference) => void;
}) {
  const [name, setName] = useState(conference?.name ?? "");
  const [acronym, setAcronym] = useState(conference?.acronym ?? "");
  const [website, setWebsite] = useState(conference?.website_url ?? "");
  const [cfp, setCfp] = useState(conference?.cfp_url ?? "");
  const [deadline, setDeadline] = useState(isoToLocalInput(conference?.submission_deadline));
  const [location, setLocation] = useState(conference?.location ?? "");
  const [notes, setNotes] = useState(conference?.notes ?? "");
  const [dates, setDates] = useState<DateRow[]>(
    (conference?.important_dates ?? []).map((d) => ({ label: d.label, date: isoToLocalInput(d.date) }))
  );
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    const deadlineIso = localInputToIso(deadline);
    if (!deadlineIso) {
      setError("A submission deadline is required.");
      return;
    }
    const important: ImportantDate[] = dates
      .filter((d) => d.label.trim() && d.date)
      .map((d) => ({ label: d.label.trim(), date: localInputToIso(d.date)! }));
    const input = {
      name,
      acronym: acronym || null,
      website_url: website || null,
      cfp_url: cfp || null,
      submission_deadline: deadlineIso,
      important_dates: important,
      location: location || null,
      notes,
    };
    setSaving(true);
    try {
      const saved = conference
        ? await updateConference(conference.id, input)
        : await createConference({ ...input, project_id: projectId ?? null });
      onSaved(saved);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      wide
      title={conference ? "Edit conference" : "Add conference deadline"}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button type="submit" form="conference-form" loading={saving}>Save</Button>
        </>
      }
    >
      <form id="conference-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <Field label="Conference name">{(id) => <Input id={id} required value={name} onChange={(e) => setName(e.target.value)} />}</Field>
        <Field label="Acronym">{(id) => <Input id={id} value={acronym} onChange={(e) => setAcronym(e.target.value)} />}</Field>
        <Field label="Official website">{(id) => <Input id={id} type="url" value={website} onChange={(e) => setWebsite(e.target.value)} />}</Field>
        <Field label="Call for papers URL">{(id) => <Input id={id} type="url" value={cfp} onChange={(e) => setCfp(e.target.value)} />}</Field>
        <Field label="Submission deadline" hint="Enter it in your local time; it is stored in UTC.">
          {(id) => <Input id={id} type="datetime-local" required value={deadline} onChange={(e) => setDeadline(e.target.value)} />}
        </Field>
        <Field label="Location">{(id) => <Input id={id} value={location} onChange={(e) => setLocation(e.target.value)} />}</Field>
        <fieldset className="space-y-2 sm:col-span-2">
          <legend className="text-sm font-medium text-slate-700">Important dates</legend>
          {dates.map((row, index) => (
            <div key={index} className="flex gap-2">
              <Input aria-label="Date label" placeholder="e.g. Notification" value={row.label} onChange={(e) => setDates(dates.map((d, i) => (i === index ? { ...d, label: e.target.value } : d)))} />
              <Input aria-label="Date" type="datetime-local" value={row.date} onChange={(e) => setDates(dates.map((d, i) => (i === index ? { ...d, date: e.target.value } : d)))} />
              <Button size="sm" variant="ghost" onClick={() => setDates(dates.filter((_, i) => i !== index))}>Remove</Button>
            </div>
          ))}
          <Button size="sm" variant="secondary" onClick={() => setDates([...dates, { label: "", date: "" }])}>Add date</Button>
        </fieldset>
        <div className="sm:col-span-2">
          <Field label="Notes">{(id) => <Textarea id={id} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />}</Field>
        </div>
        {error && <div className="sm:col-span-2"><Alert>{error}</Alert></div>}
      </form>
    </Modal>
  );
}
