\# RootLens Shared Schemas



\## Incident



Incident being investigated.



\## Evidence



id

incident\_id

timestamp

source

event\_type

service

version

observation

metadata

provenance



\## Hypothesis



id

statement

status

score

supporting\_evidence\_ids

contradicting\_evidence\_ids

missing\_evidence

disconfirming\_condition

reasoning



\## AgentAction



tool

arguments

reason

target\_hypotheses

missing\_evidence\_addressed



\## ToolResult



tool

status

evidence\_ids\[]

observations\[]

provenance\[]



\## InvestigationState



incident

goal

time\_window

iteration

actions\_taken\[]

evidence\_ids\[]

hypotheses\[]

observations\[]

missing\_evidence\[]

candidate\_actions\[]

selected\_action

action\_reason

evidence\_score

verification\_status

status

audit\_events\[]

