# a71

*English summary (added by a maintainer in review):* the agent issues dependent tool calls together in one model response instead of in order. `attach_label` needs the `shipment_id` that only `book_shipment` returns, and `set_order_status` should follow the `get_order` read. In `bulk_ship` the cancelled order `ORD-7106` was updated in the same response that read it, so its update failed while the other two stayed, leaving a partial batch (2 of 3). Checks explained: T1-009, T2-009. The step that should differ: read first and wait for the results, then issue only the dependent calls the results allow, and roll back or skip the batch if one call cannot succeed. `carrier_timeout` does not show this failure.

السبب الجذري: يصدر الوكيل استدعاءات الأدوات التابعة في رد نموذج واحد بدل ترتيبها: فهو يطلق في الدفعة نفسها استدعاءات تحتاج إلى نتائج استدعاءات سابقة — مثل `attach_label` الذي يحتاج إلى `shipment_id` الذي لا يعيده إلا `book_shipment`، و`set_order_status` الذي يحتاج إلى قراءة حالة الطلب من `get_order` — دون انتظار تلك النتائج. ولأن تحديث `ORD-7106` صدر في الرد نفسه الذي صدرت فيه قراءته، لم يستخدم الوكيل نتيجة القراءة، فنجح تحديثا الطلبين القابلين للشحن بينما فشل تحديث الطلب الملغى بالخطأ `order is cancelled, status is final`، واستمرت دفعة جزئية (2 من 3) بدل أن تكون كلها أو لا شيء.

الفحوصات التي يفسرها هذا السبب: T1-009، T2-009.

الخطوة التي كان يجب أن تختلف: القراءة أولًا ثم الفعل — إصدار `get_order` والحجز أولًا وانتظار نتائجهما، ثم إصدار الاستدعاءات التابعة فقط: `attach_label` بمعرّف الشحنة المُعاد، و`set_order_status` للطلبات التي تسمح حالتها بذلك؛ وإن تعذّر أي استدعاء في الدفعة، عدم تحديث أي طلب منها أو التراجع عن التحديثات التي تمت.

الدليل: التتبع المسجّل `agents/a71/traces/a71.otlp.jsonl`، والأمر `agentest std run --agent a71 --format md`.

- في تشغيل `canon` (وفي `label_order`) أصدر رد النموذج الأول الاستدعاءات الخمسة كلها دفعة واحدة: `get_order` و`reserve_stock` و`book_shipment` و`attach_label` و`set_order_status`، رغم أن `attach_label` يحتاج إلى `shipment_id` (`SHP-9002`) الذي يعيده `book_shipment`.
- في تشغيل `bulk_ship` أصدر رد نموذج واحد `get_order` و`set_order_status` للطلبات `ORD-7104` و`ORD-7105` و`ORD-7106` معًا؛ فنجح تحديث `ORD-7104` و`ORD-7105` إلى `shipped`، وفشل تحديث `ORD-7106` بالخطأ `order is cancelled, status is final`، وبقي التحديثان الناجحان.
- في المقابل، في تشغيل `carrier_timeout` فشل الحجز بمهلة (`timeout: carrier delhivery API did not respond within 30s`)، فانتظر الوكيل النتيجة وعوّض بشكل صحيح: أعاد المخزون (`MN-270` من 1 إلى 2) وحوّل الحالة إلى `on_hold`. هذا التشغيل لا يُظهر الفشل.
