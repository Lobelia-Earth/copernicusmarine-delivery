# Copernicus Marine Producers Toolbox

Library Python to help user upload data to the MDS.

TODO:

- [ ] Find a proper name
- [ ] Make it happen
- [ ] Work on the dependencies to define environments that is supports (e.g. Python versions etc)
- [ ] See how to relate credentials and getting producer id
- [ ] Allow users to pass folders for ease of use.

Problems:

- When you have an interface like this with specific commands, it doesn't make sense to have manifests with several operations. Or we have to change and have a generic function `deliver` that takes as argument: `delete=` and `upload=`.
- Concurrency: we want to be sure that the commands of the user are done in order (example, a delete before an upload) so we need to be sure to know which one arrived first (right now we only distinguish by the second). Corollary: how do we want the tool to be used i.e., the user might want to loop over a command => how do we handle that to be sure the order is respected and to limit the overhead. Or maybe we want to forbid this behavior.
