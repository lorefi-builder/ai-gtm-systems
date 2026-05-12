export class AlreadyActionedError extends Error {
  constructor(id: string) {
    super(
      `Row ${id} is no longer in pending_review — another reviewer beat us to it.`,
    );
    this.name = "AlreadyActionedError";
  }
}
