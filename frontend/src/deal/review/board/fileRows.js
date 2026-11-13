/*
 * The client's files in the To review lane (plan.md §8.8; L9, L125; slice 59): where each one's read stands, and
 * whether "Read with Claude ▸" is offered — only when a reader reads its kind (the server's `reader`: a renewal or a
 * quote goes to the quote reader, a paper questionnaire to the questionnaire's) and no read of it is going, waiting
 * for review or used.
 */

const READ_WORDS = {
  reading: 'Being read',
  waiting: 'Read — waiting for review',
  used: 'Read and used',
};

export function readWords(file) {
  return READ_WORDS[file?.read] || '';
}

export function canRead(file) {
  return Boolean(file?.reader) && !file?.read;
}
