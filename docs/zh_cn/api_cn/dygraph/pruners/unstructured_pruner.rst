非结构化稀疏
================

UnstructuredPruner
----------

.. py:class:: paddleslim.UnstructuredPruner(model, mode, threshold=0.01, ratio=0.55, prune_params_type=None, skip_params_func=None, local_sparsity=False)

`源代码 <https://github.com/PaddlePaddle/PaddleSlim/blob/develop/paddleslim/dygraph/prune/unstructured_pruner.py>`_

对于神经网络中的参数进行非结构化稀疏。非结构化稀疏是指，根据某些衡量指标，将不重要的参数置0。其不按照固定结构剪裁（例如一个通道等），这是和结构化剪枝的主要区别。

**参数：**

- **model(paddle.nn.Layer)** - 待剪裁的动态图模型。
- **mode(str)** - 稀疏化的模式，目前支持的模式有：'ratio'和'threshold'。在'ratio'模式下，会给定一个固定比例，例如0.5，然后所有参数中重要性较低的50%会被置0。类似的，在'threshold'模式下，会给定一个固定阈值，例如1e-5，然后重要性低于1e-5的参数会被置0。
- **ratio(float)** - 稀疏化比例期望，只有在 mode=='ratio' 时才会生效。
- **threshold(float)** - 稀疏化阈值期望，只有在 mode=='threshold' 时才会生效。
- **prune_params_type(String)** - 用以指定哪些类型的参数参与稀疏。目前只支持None和"conv1x1_only"两个选项，后者表示只稀疏化1x1卷积。而前者表示稀疏化除了归一化层的参数。
- **skip_params_func(function)** - 一个指向function的指针，该function定义了哪些参数不应该被剪裁，默认（None）时代表所有归一化层参数不参与剪裁。示例代码如下：

.. code-block:: python

  NORMS_ALL = [ 'BatchNorm', 'GroupNorm', 'LayerNorm', 'SpectralNorm', 'BatchNorm1D',
      'BatchNorm2D', 'BatchNorm3D', 'InstanceNorm1D', 'InstanceNorm2D',
      'InstanceNorm3D', 'SyncBatchNorm', 'LocalResponseNorm' ]

  def _get_skip_params(model):
      """
      This function is used to check whether the given model's layers are valid to be pruned.
      Usually, the convolutions are to be pruned while we skip the normalization-related parameters.
      Deverlopers could replace this function by passing their own when initializing the UnstructuredPuner instance.

      Args:
        - model(Paddle.nn.Layer): the current model waiting to be checked.
      Return:
        - skip_params(set<String>): a set of parameters' names
      """
      skip_params = set()
      for _, sub_layer in model.named_sublayers():
          if type(sub_layer).__name__.split('.')[-1] in NORMS_ALL:
              skip_params.add(sub_layer.full_name())
      return skip_params

..

- **local_sparsity(bool)** - 剪裁比例（ratio）应用的范围：local_sparsity 开启时意味着每个参与剪裁的参数矩阵稀疏度均为 'ratio'， 关闭时表示只保证模型整体稀疏度达到'ratio'，但是每个参数矩阵的稀疏度可能存在差异。

**返回：** 一个UnstructuredPruner类的实例。

**示例代码：**

.. code-block:: python

  import paddle
  from paddleslim import UnstructuredPruner
  from paddle.vision.models import LeNet as net
  import numpy as np

  place = paddle.set_device('cpu')
  model = net(num_classes=10)

  pruner = UnstructuredPruner(model, mode='ratio', ratio=0.55)

..

  .. py:method:: paddleslim.UnstructuredPruner.step()

  更新稀疏化的阈值，如果是'threshold'模式，则维持设定的阈值，如果是'ratio'模式，则根据优化后的模型参数和设定的比例，重新计算阈值。该函数调用在训练过程中每个batch的optimizer.step()之后。

  **示例代码：**

  .. code-block:: python

    import paddle
    from paddleslim import UnstructuredPruner
    from paddle.vision.models import LeNet as net
    import numpy as np

    place = paddle.set_device('cpu')
    model = net(num_classes=10)
    pruner = UnstructuredPruner(model, mode='ratio', ratio=0.55)

    print(pruner.threshold)
    pruner.step()
    print(pruner.threshold) # 可以看出，这里的threshold和上面打印的不同，这是因为step函数根据设定的ratio更新了threshold数值，便于剪裁操作。

  ..

  .. py:method:: paddleslim.UnstructuredPruner.update_params()

  每一步优化后，重制模型中本来是0的权重。这一步通常用于模型evaluation和save之前，确保模型的稀疏率。

  **示例代码：**

  .. code-block:: python

    import paddle
    from paddleslim import UnstructuredPruner
    from paddle.vision.models import LeNet as net
    import numpy as np

    place = paddle.set_device('cpu')
    model = net(num_classes=10)
    pruner = UnstructuredPruner(model, mode='threshold', threshold=0.5)

    sparsity = UnstructuredPruner.total_sparse(model)
    print(sparsity)
    pruner.step()
    pruner.update_params()
    sparsity = UnstructuredPruner.total_sparse(model)
    print(sparsity) # 可以看出，这里打印的模型稀疏度与上述不同，这是因为update_params()函数置零了所有绝对值小于0.5的权重。

  ..

  .. py:method:: paddleslim.UnstructuredPruner.set_static_masks()

  这个API比较特殊，一般情况下不会用到。只有在【基于 FP32 稀疏化模型】进行量化训练时需要调用，因为需要固定住原本被置0的权重，保持0不变。具体来说，对于输入的 parameters=[0, 3, 0, 4, 5.5, 0]，会生成对应的mask为：[0, 1, 0, 1, 1, 0]。而且在训练过程中，该 mask 数值不会随 parameters 更新（训练）而改变。在评估/保存模型之前，可以通过调用 pruner.update_params() 将mask应用到  parameters 上，从而达到『在训练过程中 parameters 中数值为0的参数不参与训练』的效果。

  **示例代码：**

  .. code-block:: python

    import paddle
    from paddleslim import UnstructuredPruner
    from paddle.vision.models import LeNet as net
    import numpy as np

    place = paddle.set_device('cpu')
    model = net(num_classes=10)
    pruner = UnstructuredPruner(model, mode='threshold', threshold=0.5)

    '''注释中为量化训练相关代码，以及参数导入
    QAT configs and APIs
    restore the sparse FP32 weights
    '''

    pruner.set_static_masks()
    # quantization-aware training a batch
    pruner.update_params()# 这一行代码需要在模型eval和保存前调用。
    # eval or save pruned model

  ..

  ..  py:method:: paddleslim.UnstructuredPruner.total_sparse(model)

  UnstructuredPruner中的静态方法，用于计算给定的模型（model）的稀疏度并返回。该方法为静态方法，是考虑到在单单做模型评价的时候，我们就不需要初始化一个UnstructuredPruner示例了。

  **参数：**

  -  **model(paddle.nn.Layer)** - 要计算稀疏度的目标网络。

  **返回：**
  
  - **sparsity(float)** - 模型的稀疏度。

  **示例代码：**

  .. code-block:: python

    import paddle
    from paddleslim import UnstructuredPruner
    from paddle.vision.models import LeNet as net
    import numpy as np

    place = paddle.set_device('cpu')
    model = net(num_classes=10)
    sparsity = UnstructuredPruner.total_sparse(model)
    print(sparsity)
    
  ..

  ..  py:method:: paddleslim.UnstructuredPruner.total_sparse_conv1x1(model)

  UnstructuredPruner中的静态方法，用于计算给定的模型（model）的1x1卷积的稀疏度并返回。该方法为静态方法，是考虑到在单单做模型评价的时候，我们就不需要初始化一个UnstructuredPruner示例了。

  **参数：**

  -  **model(paddle.nn.Layer)** - 要计算稀疏度的目标网络。

  **返回：**

  - **sparsity(float)** - 模型的1x1卷积稀疏度。

  **示例代码：**

  .. code-block:: python

    import paddle
    from paddleslim import UnstructuredPruner
    from paddle.vision.models import MobileNetV1 as net
    import numpy as np

    place = paddle.set_device('cpu')
    model = net(num_classes=10)
    sparsity = UnstructuredPruner.total_sparse_conv1x1(model)
    print(sparsity)

  ..

  .. py:method:: paddleslim.UnstructuredPruner.summarize_weights(model, ratio=0.1)

  该函数用于估计预训练模型中参数的分布情况，尤其是在不清楚如何设置threshold的数值时，尤为有用。例如，当输入为ratio=0.1时，函数会返回一个数值v，而绝对值小于v的权重的个数占所有权重个数的(100*ratio%)。

  **参数：**

  - **model(paddle.nn.Layer)** - 要分析权重分布的目标网络。
  - **ratio(float)** - 需要查看的比例情况，具体如上方法描述。

  **返回：**

  - **threshold(float)** - 和输入ratio对应的阈值。开发者可以根据该阈值初始化UnstructuredPruner。

  **示例代码：**

  .. code-block:: python

    import paddle
    from paddleslim import UnstructuredPruner
    from paddle.vision.models import LeNet as net
    import numpy as np

    place = paddle.set_device('cpu')
    model = net(num_classes=10)
    pruner = UnstructuredPruner(model, mode='ratio', ratio=0.55)

    threshold = pruner.summarize_weights(model, 0.5)
    print(threshold)

  ..

GMPUnstructuredPruner
----------

`源代码 <https://github.com/PaddlePaddle/PaddleSlim/blob/develop/paddleslim/dygraph/prune/unstructured_pruner.py>`_

.. py:class:: paddleslim.GMPUnstructuredPruner(model, ratio=0.55, prune_params_type=None, skip_params_func=None, local_sparsity=False, configs=None)

该类是UnstructuredPruner的一个子类，通过覆盖step()方法，优化了训练策略，使稀疏化训练更易恢复到稠密模型精度。其他方法均继承自父类。

**参数：**

- **model(paddle.nn.Layer)** - 待剪裁的动态图模型。
- **ratio(float)** - 稀疏化比例期望，只有在 mode=='ratio' 时才会生效。
- **prune_params_type(str)** - 用以指定哪些类型的参数参与稀疏。目前只支持None和"conv1x1_only"两个选项，后者表示只稀疏化1x1卷积。而前者表示稀疏化除了归一化层的参数。
- **skip_params_func(function)** - 一个指向function的指针，该function定义了哪些参数不应该被剪裁，默认（None）时代表所有归一化层参数不参与剪裁。
- **local_sparsity(bool)** - 剪裁比例（ratio）应用的范围：local_sparsity 开启时意味着每个参与剪裁的参数矩阵稀疏度均为 'ratio'， 关闭时表示只保证模型整体稀疏度达到'ratio'，但是每个参数矩阵的稀疏度可能存在差异。
- **configs(Dict)** - 传入额外的训练超参用以指导GMP训练过程。各参数介绍如下：

.. code-block:: python
               
  {'stable_iterations': int} # the duration of stable phase in terms of global iterations
  {'pruning_iterations': int} # the duration of pruning phase in terms of global iterations
  {'tunning_iterations': int} # the duration of tunning phase in terms of global iterations
  {'resume_iteration': int} # the start timestamp you want to train from, in terms if global iteration
  {'pruning_steps': int} # the total times you want to increase the ratio
  {'initial_ratio': float} # the initial ratio value
        
..

**返回：** 一个GMPUnstructuredPruner类的实例

.. code-block:: python

  import paddle
  from paddleslim import GMPUnstructuredPruner
  from paddle.vision.models import LeNet as net
  import numpy as np

  place = paddle.set_device('cpu')
  model = net(num_classes=10)

  configs = {
      'stable_iterations': 0,
      'pruning_iterations': 1000,
      'tunning_iterations': 1000,
      'resume_iteration': 0,
      'pruning_steps': 10,
      'initial_ratio': 0.15,
  }

  pruner = GMPUnstructuredPruner(model, ratio=0.55, configs=configs)

..

  .. py:method:: paddleslim.GMPUnstructuredPruner.step()

  更新稀疏化的阈值：根据优化后的模型参数和设定的比例，重新计算阈值。该函数调用在训练过程中每个batch的optimizer.step()之后。

  **示例代码：**

  .. code-block:: python

    import paddle
    from paddleslim import GMPUnstructuredPruner
    from paddle.vision.models import LeNet as net
    import numpy as np

    place = paddle.set_device('cpu')
    model = net(num_classes=10)

    configs = {
        'stable_iterations': 0,
        'pruning_iterations': 1000,
        'tunning_iterations': 1000,
        'resume_iteration': 0,
        'pruning_steps': 10,
        'initial_ratio': 0.15,
    }

    pruner = GMPUnstructuredPruner(model, ratio=0.55, configs=configs)

    print(pruner.threshold)
    for i in range(200):
        pruner.step()
    print(pruner.threshold) # 可以看出，这里的threshold和上面打印的不同，这是因为step函数根据设定的ratio更新了threshold数值，便于剪裁操作。

  ..

