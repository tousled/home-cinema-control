# Take part in HCC improvements

[Home](../README.en.md) · [Privacy](telemetry.en.md) · [Español](participar.md)

**Take part** groups short questions and interests to help prioritize HCC
improvements. No account or email is required. You can use HCC without answering
or sharing technical signals.

## Choose whether to help

Consent to share technical signals is optional and survives updates. Opening **Take part** does not enable it or repeat
a declined invitation.

1. Open **Take part** in the HCC menu.
2. To send answers or votes, open **Diagnostics** and find **Help improve HCC**.
   Consent is managed there, separately from the questions.
3. Expand **What data do we send, and why?** to review the data.
4. Click **Help HCC** to enable sharing. In the invitation, **Not now** keeps
   your previous choice without showing that invitation again.

Telemetry uses a pseudonymous code to link signals from your installation.
It does not guarantee absolute anonymity. Support reports you choose to review
and share manually follow a separate process.

<p align="center">
  <img src="../assets/screenshots/install/12-help-hcc.png" alt="Optional consent invitation in Spanish, showing Help HCC and Not now in a test instance" width="860"/>
</p>

## Answer a short question

Questions are included in each HCC version. When questions are unanswered,
Control Room shows a discreet invitation outside playback. It does not open a modal.

1. Open **Take part**.
2. Select the options you would use. For Emby and Jellyfin, you can select several, while **I don't need this** excludes all other options.
   For how you start a movie or which player to support next, select just one option.
3. Click **Next** to move on: HCC automatically saves your selected answer if it changed. **Previous** does the same when returning to an earlier question. Use **Finish** for the last question. You can skip an unanswered question without submitting it. If saving fails, you stay on the current question with the selection intact.

**Not now** postpones the question and keeps the indicator. **Not interested**
hides only that question. Your choice survives reloads, restarts, and updates.
A question with another identifier can show its own indicator without
restoring dismissed questions.

A locally saved answer does not prove the hub has received it. Failed
deliveries use HCC's existing bounded queue and retries. The hub keeps the
history and counts the last received answer per installation/question,
without counting another installation for each edit.

## Change your interests

The list describes possible improvements, not available compatibility or
implementation promises. Samsung (local proof of concept, model-specific
validation pending), TCL, Hisense and Philips (OS-dependent feasibility)
remain individual TV candidates; Zidoo and Dune HD are separate choices.
Panasonic, Xiaomi, Roku and Vizio are not presented as immediate candidates
because no sufficiently validated, prioritized integration path has been found. Sony TV, Home Assistant, OPPO, and Trinnov Altitude
are absent as new integrations because HCC already supports them.
Historical grouped votes are preserved.

1. Under **Take part**, select or clear your interests.
2. Click **Save my vote**, including when you have cleared all choices.

The last received vote stays in effect until you change it. Votes for retired
categories remain in the history. Votes remain closed choices. Hue/Ambilight is not offered as a pending
interest because no concrete proposal has been identified.

## Suggest another improvement

Below the questions is an optional field limited to 400 characters.
Typing alone **does not send anything**. Your text is shared only when you
press **Send comment** while participation consent is enabled.
Do not include personal details, IPs, passwords or file paths.
The text can remain temporarily in the local retry queue and is visible
only in the receiver's private administrator section. HCC says
**queued for delivery**, not that the receiver has confirmed it.

## Stop sharing signals

Under **Help improve HCC**, click **Disable**. HCC cancels pending deliveries
and clears the local queue. It tries to report revocation once, without
storing or retrying it. Data already received by the hub is not deleted.
Reopening **Take part** does not resend saved answers or enable consent.
See the [telemetry contract](telemetry.en.md) for fields and retention limits.
